"""Real Stage A/B curriculum run for the PINN baseline, against real
HURDAT2 tracks and cached real GriddedFields (#22).

`models.pinn.build_pinn`'s own docstring is explicit that this is a
*residual corrector applied on top of a candidate forecast* -- its inputs
are an environment vector and an already-existing candidate track, not raw
observations, and its correction is zero-initialised so an untrained
corrector is the identity. That makes PINN's real-data problem different
in kind from LSTM/CNN/Transformer/GNN: it needs another model's real
prediction to correct, not just its own feature source.

This runner supplies that by training a small internal LSTM as the
candidate generator (`_train_candidate_lstm`), on the same real tracks,
each time it runs -- self-contained and reproducible, rather than reaching
for a specific external checkpoint URI that may or may not exist. The
candidate generator trains on raw (unstandardised) displacement targets:
its role here is only to produce a real, non-trivial forecast for PINN to
correct, not to be independently well-tuned -- `training.real_run`'s LSTM
runner is the one that actually cares about candidate-generator quality.

The environment vector is real: `data.features.compute_environment_features`
against the window's cached `GriddedFields` (the same real cache
CNN/Transformer/GNN read). PINN's own coordinate convention is absolute
(lat, lon, wind), not the east/north displacement the other runners use
(`models.pinn.physics_residuals` operates on absolute lat/lon directly),
so both the candidate and the true target are converted to absolute
positions here before training.

`physics_residuals(track, dt_hours)` assumes uniform time spacing between
consecutive lead times, but `models.base.DEFAULT_LEADS` is NOT uniformly
spaced (12/24/36/48h are 12h apart; 48/72/96/120h are 24h apart) -- passing
one dt_hours across the full 7-lead sequence would silently misreport speed
by up to 4x on the irregular legs. This runner applies the physics penalty
only to the first four leads (12/24/36/48h), which *are* uniformly 12h
apart, with `dt_hours=12.0` -- a real, valid subsequence, not the full one.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from ..data.besttrack import Track, WorkingTrackNoise
from ..data.features import FEATURE_NAMES, compute_environment_features
from ..data.gridded_cache import FetchTask, cache_path, load_cached_fields
from ..data.sources import Flavor
from ..data.splits import Split, assign_splits, filter_tracks
from ..data.storm_relative import STORM_RELATIVE_COLUMNS, storm_relative_sequence
from ..metrics.track import ForecastPoint, VerificationPair, to_metric_dict, verify
from ..models.base import DEFAULT_LEADS, require_torch
from ..tracking.checkpoint_store import CheckpointStore
from .capacity_ablation import SEQUENCE_LENGTH
from .curriculum import Curriculum, CurriculumRun, StageResult, StageSpec
from .device import get_device
from .promotion import MetricSet
from .real_run import boundaries_for_flavor, displacement_to_latlon, iter_stage_windows

#: Weights on each physics_residuals term in the training loss -- small
#: relative to the track/intensity MSE, so physics acts as a soft
#: regulariser rather than dominating early training when the corrector
#: (zero-initialised) is still near-identity.
PHYSICS_LOSS_WEIGHTS: dict[str, float] = {"speed": 0.01, "curvature": 0.01, "hemisphere": 0.01}
#: Leads 12/24/36/48h -- the uniformly-12h-spaced prefix of DEFAULT_LEADS
#: physics_residuals' constant-dt_hours assumption is valid for.
_PHYSICS_LEAD_COUNT = 4
_PHYSICS_DT_HOURS = 12.0


@dataclass(frozen=True, slots=True)
class PinnStageSamples:
    x_track: np.ndarray  # (N, SEQUENCE_LENGTH, 5) -- for the candidate generator
    environment: np.ndarray  # (N, len(FEATURE_NAMES))
    y: np.ndarray  # (N, n_leads, 3) -- true (dx_east_nm, dy_north_nm, wind_kt)
    mask: np.ndarray
    base_lat: np.ndarray
    base_lon: np.ndarray

    def __len__(self) -> int:
        return len(self.x_track)


def build_pinn_samples(
    tracks: list[Track],
    cache_dir: Path | str,
    rng: np.random.Generator,
    n_augment: int = 1,
    noise: WorkingTrackNoise | None = None,
) -> PinnStageSamples:
    """Same windows/targets as `real_run.build_stage_samples`, plus the
    real environment vector for the window's current fix (from cached
    `GriddedFields`). A fix with no cached file yet is skipped."""
    cache_dir = Path(cache_dir)
    x_track_rows: list[np.ndarray] = []
    env_rows: list[np.ndarray] = []
    y_rows: list[np.ndarray] = []
    mask_rows: list[np.ndarray] = []
    base_lat_rows: list[float] = []
    base_lon_rows: list[float] = []

    for sw in iter_stage_windows(tracks, rng, n_augment, noise):
        task = FetchTask(
            storm_id=sw.storm_id, valid_time=sw.current.valid_time,
            lat=sw.current.lat, lon=sw.current.lon,
        )
        path = cache_path(cache_dir, task)
        if not path.exists():
            continue
        fields = load_cached_fields(path)
        env = compute_environment_features(fields).values

        x_track_rows.append(storm_relative_sequence(sw.window))
        env_rows.append(env)
        y_rows.append(sw.y)
        mask_rows.append(sw.mask)
        base_lat_rows.append(sw.current.lat)
        base_lon_rows.append(sw.current.lon)

    n_leads = len(DEFAULT_LEADS)
    if not x_track_rows:
        return PinnStageSamples(
            x_track=np.empty((0, SEQUENCE_LENGTH, len(STORM_RELATIVE_COLUMNS))),
            environment=np.empty((0, len(FEATURE_NAMES))),
            y=np.empty((0, n_leads, 3)),
            mask=np.empty((0, n_leads), dtype=bool),
            base_lat=np.empty((0,)),
            base_lon=np.empty((0,)),
        )
    return PinnStageSamples(
        x_track=np.stack(x_track_rows),
        environment=np.stack(env_rows),
        y=np.stack(y_rows),
        mask=np.stack(mask_rows),
        base_lat=np.array(base_lat_rows),
        base_lon=np.array(base_lon_rows),
    )


def _train_candidate_lstm(
    train_tracks: list[Track],
    rng: np.random.Generator,
    *,
    n_augment: int = 3,
    device=None,
    hidden_dim: int = 64,
    epochs: int = 30,
    lr: float = 1e-3,
):
    """A small internal LSTM trained on raw (unstandardised) displacement
    targets -- see module docstring for why this doesn't reuse
    `real_run.train_lstm_stage`'s standardised training (its z-score stats
    aren't returned, and PINN corrects whatever this produces rather than
    depending on it being independently well-tuned)."""
    from ..models.lstm import build_lstm
    from .real_run import build_stage_samples

    torch = require_torch()
    device = device or get_device()

    samples = build_stage_samples(train_tracks, rng, n_augment=n_augment)
    if len(samples) == 0:
        raise ValueError("no track samples to train the PINN candidate generator on")

    model, _spec = build_lstm(
        input_dim=len(STORM_RELATIVE_COLUMNS), hidden_dim=hidden_dim, lead_hours=DEFAULT_LEADS,
    )
    model.to(device)

    xt = torch.as_tensor(samples.x, dtype=torch.float32, device=device)
    yt = torch.as_tensor(samples.y, dtype=torch.float32, device=device)
    mt = torch.as_tensor(samples.mask, dtype=torch.float32, device=device).unsqueeze(-1)

    opt = torch.optim.Adam(model.parameters(), lr=lr)
    model.train()
    for _ in range(epochs):
        opt.zero_grad()
        diff2 = (model(xt) - yt) ** 2 * mt
        loss = diff2.sum() / mt.sum().clamp(min=1.0)
        loss.backward()
        opt.step()
    model.eval()
    return model


def _candidate_and_true_absolute(
    candidate_model, samples: PinnStageSamples, device
) -> tuple[np.ndarray, np.ndarray]:
    """Run the candidate generator and convert both its (raw-unit
    displacement) prediction and the true target to absolute (lat, lon,
    wind) -- PINN's own coordinate convention, unlike the other runners'
    displacement-relative-to-current-fix convention."""
    torch = require_torch()
    with torch.no_grad():
        xt = torch.as_tensor(samples.x_track, dtype=torch.float32, device=device)
        pred_disp = candidate_model(xt).cpu().numpy()

    n, n_leads, _ = pred_disp.shape
    candidate_abs = np.zeros_like(pred_disp)
    true_abs = np.zeros_like(samples.y)
    for si in range(n):
        base_lat, base_lon = samples.base_lat[si], samples.base_lon[si]
        for li in range(n_leads):
            plat, plon = displacement_to_latlon(base_lat, base_lon, *pred_disp[si, li, :2])
            candidate_abs[si, li] = [plat, plon, pred_disp[si, li, 2]]
            tlat, tlon = displacement_to_latlon(base_lat, base_lon, *samples.y[si, li, :2])
            true_abs[si, li] = [tlat, tlon, samples.y[si, li, 2]]
    return candidate_abs, true_abs


def _freeze_pinn_trunk(model, frozen_modules: tuple[str, ...]) -> None:
    """PhysicsCorrector's submodules are `.trunk` and `.correction`
    (not `.head`) -- 'encoder' here means everything outside
    `.correction`, the architecture's own final residual layer."""
    if "encoder" not in frozen_modules:
        return
    for name, param in model.named_parameters():
        if not name.startswith("correction."):
            param.requires_grad = False


def train_pinn_stage(
    model,
    candidate_model,
    stage: StageSpec,
    train_tracks: list[Track],
    val_tracks: list[Track],
    cache_dir: Path | str,
    rng: np.random.Generator,
    *,
    n_augment: int = 3,
    device=None,
) -> tuple[object, float, float, MetricSet]:
    """PINN analog of `real_run.train_lstm_stage`. Loss is masked
    track/intensity MSE (absolute-coordinate space) plus a small weighted
    `models.pinn.physics_residuals` penalty over the leads it's valid for
    (see module docstring)."""
    if not train_tracks or not val_tracks:
        raise ValueError(f"stage {stage.name}: empty train or val storm set")

    torch = require_torch()
    from ..models.pinn import physics_residuals

    device = device or get_device()

    train_samples = build_pinn_samples(train_tracks, cache_dir, rng, n_augment=n_augment)
    val_samples = build_pinn_samples(val_tracks, cache_dir, rng, n_augment=1)
    if len(train_samples) == 0 or len(val_samples) == 0:
        raise ValueError(
            f"stage {stage.name}: no cached GriddedFields matched the given tracks in "
            f"{cache_dir} -- has data.era5_cache/data.gdas_cache fetched anything yet?"
        )

    env_mean = train_samples.environment.mean(axis=0)
    env_std = train_samples.environment.std(axis=0)
    env_std[env_std < 1e-8] = 1.0
    env_train_z = (train_samples.environment - env_mean) / env_std
    env_val_z = (val_samples.environment - env_mean) / env_std

    cand_train, true_train = _candidate_and_true_absolute(candidate_model, train_samples, device)
    cand_val, true_val = _candidate_and_true_absolute(candidate_model, val_samples, device)

    _freeze_pinn_trunk(model, stage.frozen_modules)
    model.to(device)

    def masked_mse(pred, target, mask3):
        diff2 = (pred - target) ** 2 * mask3
        return diff2.sum() / mask3.sum().clamp(min=1.0)

    envt = torch.as_tensor(env_train_z, dtype=torch.float32, device=device)
    candt = torch.as_tensor(cand_train, dtype=torch.float32, device=device)
    truet = torch.as_tensor(true_train, dtype=torch.float32, device=device)
    mt = torch.as_tensor(train_samples.mask, dtype=torch.float32, device=device).unsqueeze(-1)

    trainable = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.Adam(trainable, lr=stage.learning_rate)

    model.train()
    for _ in range(stage.epochs):
        opt.zero_grad()
        pred = model(envt, candt)
        track_loss = masked_mse(pred, truet, mt)
        residuals = physics_residuals(pred[:, :_PHYSICS_LEAD_COUNT, :], dt_hours=_PHYSICS_DT_HOURS)
        phys_loss = sum(PHYSICS_LOSS_WEIGHTS[k] * v for k, v in residuals.items())
        loss = track_loss + phys_loss
        loss.backward()
        opt.step()

    model.eval()
    with torch.no_grad():
        train_loss = float(masked_mse(model(envt, candt), truet, mt).item())

        envv = torch.as_tensor(env_val_z, dtype=torch.float32, device=device)
        candv = torch.as_tensor(cand_val, dtype=torch.float32, device=device)
        truev = torch.as_tensor(true_val, dtype=torch.float32, device=device)
        mv = torch.as_tensor(val_samples.mask, dtype=torch.float32, device=device).unsqueeze(-1)
        pred_val_t = model(envv, candv)
        val_loss = float(masked_mse(pred_val_t, truev, mv).item())
        pred_val = pred_val_t.cpu().numpy()

    pairs: list[VerificationPair] = []
    for si in range(len(val_samples)):
        for li, lead_hours in enumerate(DEFAULT_LEADS):
            if not val_samples.mask[si, li]:
                continue
            plat, plon, pwind = pred_val[si, li]
            tlat, tlon, twind = true_val[si, li]
            pairs.append(
                VerificationPair(
                    forecast=ForecastPoint(
                        lead_hours=lead_hours, lat=float(plat), lon=float(plon),
                        max_wind_kt=float(pwind),
                    ),
                    obs_lat=float(tlat),
                    obs_lon=float(tlon),
                    obs_wind_kt=float(twind),
                )
            )

    if not pairs:
        raise ValueError(f"stage {stage.name}: no verifiable (lead, sample) pairs in val")
    val_metrics = MetricSet(split="val", flavor=stage.flavor, values=to_metric_dict(verify(pairs)))
    return model, train_loss, val_loss, val_metrics


def run_pinn_curriculum(
    tracks: list[Track],
    checkpoint_store: CheckpointStore,
    era5_cache_dir: Path | str,
    gdas_cache_dir: Path | str,
    *,
    seed: int = 20260806,
    n_augment: int = 3,
    hidden_dim: int = 128,
    candidate_hidden_dim: int = 64,
    curriculum_kwargs: dict | None = None,
) -> tuple[CurriculumRun, MetricSet]:
    """Run the real Stage A -> Stage B curriculum for the PINN baseline.
    A fresh candidate-generator LSTM is trained per stage (see module
    docstring) on that stage's own train tracks before PINN is trained
    against its output.
    """
    from ..models.pinn import build_pinn

    require_torch()
    rng = np.random.default_rng(seed)
    device = get_device()
    curriculum = Curriculum.standard("pinn", **(curriculum_kwargs or {}))
    run = CurriculumRun(curriculum=curriculum)

    model = None
    val_metrics: MetricSet | None = None
    for stage in curriculum.stages:
        cache_dir = era5_cache_dir if stage.flavor is Flavor.ERA5_PRETRAIN else gdas_cache_dir
        boundaries = boundaries_for_flavor(stage.flavor)
        assignment = assign_splits(tracks, boundaries)
        train_tracks = filter_tracks(tracks, assignment, Split.TRAIN)
        val_tracks = filter_tracks(tracks, assignment, Split.VAL)

        candidate_model = _train_candidate_lstm(
            train_tracks, rng, n_augment=n_augment, device=device, hidden_dim=candidate_hidden_dim,
        )

        if model is None:
            model, _spec = build_pinn(
                input_dim=len(FEATURE_NAMES), hidden_dim=hidden_dim, lead_hours=DEFAULT_LEADS,
            )

        model, train_loss, val_loss, val_metrics = train_pinn_stage(
            model, candidate_model, stage, train_tracks, val_tracks, cache_dir, rng,
            n_augment=n_augment, device=device,
        )

        torch = require_torch()
        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = Path(tmpdir) / f"{stage.name}.pt"
            torch.save(model.state_dict(), local_path)
            key = f"checkpoints/pinn/{stage.name}/{datetime.now(UTC):%Y%m%dT%H%M%S}.pt"
            checkpoint_uri = checkpoint_store.upload(local_path, key)

        run.record(
            StageResult(
                stage_name=stage.name,
                flavor=stage.flavor,
                epochs_completed=stage.epochs,
                final_train_loss=train_loss,
                final_val_loss=val_loss,
                checkpoint_uri=checkpoint_uri,
                completed_at=datetime.now(UTC),
            )
        )

    assert val_metrics is not None
    return run, val_metrics
