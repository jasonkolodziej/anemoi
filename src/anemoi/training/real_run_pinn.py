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
from .real_run import (
    RunArtifacts,
    boundaries_for_flavor,
    displacement_to_latlon,
    iter_stage_windows,
)

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
    `GriddedFields`). A fix with no cached file yet is skipped, and so is
    one whose environment features come back non-finite -- a storm-centred
    box entirely over land has no real ERA5 SST to average
    (`data.features.area_mean`'s docstring has the full story on why this
    is a real, physical limitation and not a bug to paper over)."""
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
        try:
            env = compute_environment_features(fields).values
        except ValueError:
            continue  # non-finite feature (box entirely over land) -- skip

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


def _train_candidate_lstm_streaming(
    train_tracks: list[Track],
    rng: np.random.Generator,
    *,
    n_augment: int = 3,
    batch_size: int = 64,
    num_workers: int = 0,
    device=None,
    hidden_dim: int = 64,
    epochs: int = 30,
    lr: float = 1e-3,
):
    """Streaming analog of `_train_candidate_lstm` -- same raw
    (unstandardized) displacement targets (module docstring's reasoning
    still applies unchanged), real per-batch training via a
    `torch.utils.data.DataLoader` over a `streaming.WindowDataset` instead
    of one full-dataset GPU tensor of every training window's track
    sequence. ``num_workers`` (default 0) forwards to
    `streaming.make_dataloader` -- see that function's docstring."""
    from ..models.lstm import build_lstm
    from .streaming import WindowDataset, make_dataloader

    torch = require_torch()
    device = device or get_device()

    windows = list(iter_stage_windows(train_tracks, rng, n_augment))
    if not windows:
        raise ValueError("no track samples to train the PINN candidate generator on")

    def build_x(sw):
        return storm_relative_sequence(sw.window)

    ds = WindowDataset(windows, build_x)
    loader = make_dataloader(ds, batch_size=batch_size, shuffle=True, num_workers=num_workers)

    model, _spec = build_lstm(
        input_dim=len(STORM_RELATIVE_COLUMNS), hidden_dim=hidden_dim, lead_hours=DEFAULT_LEADS,
    )
    model.to(device)

    opt = torch.optim.Adam(model.parameters(), lr=lr)
    model.train()
    for _ in range(epochs):
        for xb, yb, mb in loader:
            xb, yb = xb.to(device), yb.to(device)
            mb = mb.to(device).unsqueeze(-1)
            opt.zero_grad()
            diff2 = (model(xb) - yb) ** 2 * mb
            loss = diff2.sum() / mb.sum().clamp(min=1.0)
            loss.backward()
            opt.step()
    model.eval()
    return model


class _PinnWindowDataset:
    """PINN-specific analog of `streaming.WindowDataset`: each item needs
    THREE things that dataset's single-array contract can't carry -- the
    real environment vector (from cached `GriddedFields`), the raw track
    window (for the candidate LSTM), and the window's base (lat, lon) the
    absolute-coordinate conversion (module docstring) is anchored to -- so
    this stays a small dataset of its own, duck-typed as a real
    ``torch.utils.data.Dataset`` the same way `WindowDataset` is, rather
    than forcing that shared class's single-``x`` shape onto PINN.
    """

    def __init__(
        self,
        windows: list,
        cache_dir: Path,
        *,
        env_mean: np.ndarray | None = None,
        env_std: np.ndarray | None = None,
    ) -> None:
        self._windows = windows
        self._cache_dir = cache_dir
        self.env_mean = env_mean
        self.env_std = env_std

    def __len__(self) -> int:
        return len(self._windows)

    def __getitem__(self, idx: int):
        sw = self._windows[idx]
        fields = load_cached_fields(cache_path(self._cache_dir, FetchTask(
            storm_id=sw.storm_id, valid_time=sw.current.valid_time,
            lat=sw.current.lat, lon=sw.current.lon,
        )))
        env = compute_environment_features(fields).values.astype(np.float32)
        if self.env_mean is not None:
            env = (env - self.env_mean) / self.env_std
        x_track = storm_relative_sequence(sw.window).astype(np.float32)
        base = np.array([sw.current.lat, sw.current.lon], dtype=np.float32)
        return env, x_track, base, sw.y.astype(np.float32), sw.mask.astype(np.float32)


def _disp_to_abs_batch(disp: np.ndarray, base: np.ndarray) -> np.ndarray:
    """Batched `_candidate_and_true_absolute`-style conversion: ``disp`` is
    ``(batch, n_leads, 3)`` raw (dx_east_nm, dy_north_nm, wind_kt), ``base``
    is ``(batch, 2)`` (lat, lon) -- returns ``(batch, n_leads, 3)`` absolute
    (lat, lon, wind_kt), PINN's own coordinate convention (module
    docstring)."""
    n, n_leads, _ = disp.shape
    out = np.zeros_like(disp)
    for si in range(n):
        base_lat, base_lon = base[si]
        for li in range(n_leads):
            lat, lon = displacement_to_latlon(base_lat, base_lon, *disp[si, li, :2])
            out[si, li] = [lat, lon, disp[si, li, 2]]
    return out


def _filter_windows_with_finite_env(windows: list, cache_dir: Path) -> list:
    """Drop windows whose real environment features come back non-finite --
    a storm-centred box entirely over land has no real ERA5 SST to average
    (`data.features.area_mean`'s docstring has the full story on this real
    physical limitation). Same "skip, don't crash" contract
    `build_pinn_samples` and `streaming.filter_windows_with_cache` already
    use, applied here *before* `_PinnWindowDataset` construction so its
    fixed-length index (`DataLoader` needs one) never contains a window
    `__getitem__` can't actually build from.

    Used for VAL windows only -- val needs no stats fit (env normalisation
    is fit on train alone, matching `train_pinn_stage`'s full-batch
    behaviour), so a plain filter is all it needs. TRAIN windows use
    `_filter_and_fit_env_stats` instead, which folds this same check into
    the stats-fitting pass so every cached file is read once during setup,
    not twice (a real, measured cost against the VM's real, growing cache
    -- see that function's docstring)."""
    kept = []
    for sw in windows:
        fields = load_cached_fields(cache_path(cache_dir, FetchTask(
            storm_id=sw.storm_id, valid_time=sw.current.valid_time,
            lat=sw.current.lat, lon=sw.current.lon,
        )))
        try:
            compute_environment_features(fields)
        except ValueError:
            continue
        kept.append(sw)
    return kept


def _filter_and_fit_env_stats(
    windows: list, cache_dir: Path
) -> tuple[list, np.ndarray | None, np.ndarray | None]:
    """TRAIN-only combined pass: drop windows whose environment features
    come back non-finite (same real land-coverage limitation
    `_filter_windows_with_finite_env`/`data.features.area_mean` document)
    *and* fit `OnlineMeanStd` over the finite ones, in one loop instead of
    two. A separate filter-then-fit (this function's earlier, simpler
    shape) reads and decompresses every cached field file TWICE before
    training even starts -- once to check finiteness, once more to
    accumulate stats -- on top of `_PinnWindowDataset`'s own per-epoch
    `DataLoader` reads. Against the VM's real, growing ERA5 cache this
    doubled setup cost was measured, not just theorised: confirmed via
    real end-to-end verification of #67's fix taking far longer than the
    other four streaming models' comparable stages. Returns
    ``(kept_windows, env_mean, env_std)`` -- ``env_mean``/``env_std`` are
    ``None`` if every window was dropped (caller must check)."""
    from .streaming import OnlineMeanStd

    kept: list = []
    acc = OnlineMeanStd(reduce_axes=(0,))
    for sw in windows:
        fields = load_cached_fields(cache_path(cache_dir, FetchTask(
            storm_id=sw.storm_id, valid_time=sw.current.valid_time,
            lat=sw.current.lat, lon=sw.current.lon,
        )))
        try:
            env = compute_environment_features(fields).values
        except ValueError:
            continue
        acc.update(env[None])
        kept.append(sw)
    if not kept:
        return kept, None, None
    env_mean, env_std = acc.finalize()
    return kept, env_mean, env_std


def train_pinn_stage_streaming(
    model,
    candidate_model,
    stage: StageSpec,
    train_tracks: list[Track],
    val_tracks: list[Track],
    cache_dir: Path | str,
    rng: np.random.Generator,
    *,
    n_augment: int = 3,
    batch_size: int = 32,
    num_workers: int = 0,
    device=None,
) -> tuple[object, float, float, MetricSet, tuple]:
    """`train_pinn_stage`'s streaming analog (`docs/streaming_dataloader.md`) --
    same return contract, same masked track/intensity loss plus physics
    penalty, real per-batch training via a `torch.utils.data.DataLoader`
    (using `_PinnWindowDataset`, see its docstring for why PINN needs its
    own rather than the shared `streaming.WindowDataset`) and online
    environment-vector standardisation instead of one full-dataset GPU
    tensor and a single `.mean()`/`.std()` call. ``num_workers`` (default
    0) forwards to `streaming.make_dataloader` -- see that function's
    docstring.
    """
    from ..models.pinn import physics_residuals
    from .streaming import filter_windows_with_cache, make_dataloader

    if not train_tracks or not val_tracks:
        raise ValueError(f"stage {stage.name}: empty train or val storm set")

    torch = require_torch()
    device = device or get_device()

    train_stage_windows = list(iter_stage_windows(train_tracks, rng, n_augment))
    train_windows_cached = filter_windows_with_cache(train_stage_windows, cache_dir)
    val_stage_windows = list(iter_stage_windows(val_tracks, rng, 1))
    val_windows = _filter_windows_with_finite_env(
        filter_windows_with_cache(val_stage_windows, cache_dir), cache_dir,
    )
    if not train_windows_cached or not val_windows:
        raise ValueError(
            f"stage {stage.name}: no cached GriddedFields matched the given tracks in "
            f"{cache_dir} -- has data.era5_cache/data.gdas_cache fetched anything yet?"
        )

    cache_dir = Path(cache_dir)
    train_windows, env_mean, env_std = _filter_and_fit_env_stats(train_windows_cached, cache_dir)
    if not train_windows:
        raise ValueError(
            f"stage {stage.name}: every cached window's environment features were "
            "non-finite (storms entirely over land?) -- nothing left to train on"
        )

    train_ds = _PinnWindowDataset(train_windows, cache_dir, env_mean=env_mean, env_std=env_std)
    val_ds = _PinnWindowDataset(val_windows, cache_dir, env_mean=env_mean, env_std=env_std)

    def collate(batch):
        envs, tracks_, bases, ys, masks = zip(*batch, strict=True)
        return np.stack(envs), np.stack(tracks_), np.stack(bases), np.stack(ys), np.stack(masks)

    train_loader = make_dataloader(
        train_ds, batch_size=batch_size, shuffle=True, num_workers=num_workers, collate_fn=collate,
    )
    val_loader = make_dataloader(
        val_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers, collate_fn=collate,
    )

    _freeze_pinn_trunk(model, stage.frozen_modules)
    model.to(device)
    candidate_model.to(device)
    candidate_model.eval()

    def masked_mse_sums(pred, target, mask3):
        diff2 = (pred - target) ** 2 * mask3
        return diff2.sum(), mask3.sum()

    def forward_batch(env_b: np.ndarray, track_b: np.ndarray, base_b: np.ndarray):
        envt = torch.as_tensor(env_b, dtype=torch.float32, device=device)
        trackt = torch.as_tensor(track_b, dtype=torch.float32, device=device)
        with torch.no_grad():
            pred_disp = candidate_model(trackt).cpu().numpy()
        candidate_abs = _disp_to_abs_batch(pred_disp, base_b)
        candt = torch.as_tensor(candidate_abs, dtype=torch.float32, device=device)
        return model(envt, candt)

    trainable = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.Adam(trainable, lr=stage.learning_rate)

    model.train()
    for _ in range(stage.epochs):
        for env_b, track_b, base_b, y_b, mask_b in train_loader:
            true_abs = _disp_to_abs_batch(y_b, base_b)
            truet = torch.as_tensor(true_abs, dtype=torch.float32, device=device)
            mt = torch.as_tensor(mask_b, dtype=torch.float32, device=device).unsqueeze(-1)
            opt.zero_grad()
            pred = forward_batch(env_b, track_b, base_b)
            diff2_sum, mask_sum = masked_mse_sums(pred, truet, mt)
            track_loss = diff2_sum / mask_sum.clamp(min=1.0)
            residuals = physics_residuals(
                pred[:, :_PHYSICS_LEAD_COUNT, :], dt_hours=_PHYSICS_DT_HOURS,
            )
            phys_loss = sum(PHYSICS_LOSS_WEIGHTS[k] * v for k, v in residuals.items())
            loss = track_loss + phys_loss
            loss.backward()
            opt.step()

    model.eval()
    with torch.no_grad():
        train_diff2, train_mask = 0.0, 0.0
        for env_b, track_b, base_b, y_b, mask_b in train_loader:
            true_abs = _disp_to_abs_batch(y_b, base_b)
            truet = torch.as_tensor(true_abs, dtype=torch.float32, device=device)
            mt = torch.as_tensor(mask_b, dtype=torch.float32, device=device).unsqueeze(-1)
            d, m = masked_mse_sums(forward_batch(env_b, track_b, base_b), truet, mt)
            train_diff2 += float(d.item())
            train_mask += float(m.item())
        train_loss = train_diff2 / max(train_mask, 1.0)

        val_diff2, val_mask = 0.0, 0.0
        pred_val_rows: list[np.ndarray] = []
        true_val_rows: list[np.ndarray] = []
        for env_b, track_b, base_b, y_b, mask_b in val_loader:
            true_abs = _disp_to_abs_batch(y_b, base_b)
            truet = torch.as_tensor(true_abs, dtype=torch.float32, device=device)
            mt = torch.as_tensor(mask_b, dtype=torch.float32, device=device).unsqueeze(-1)
            pred = forward_batch(env_b, track_b, base_b)
            d, m = masked_mse_sums(pred, truet, mt)
            val_diff2 += float(d.item())
            val_mask += float(m.item())
            pred_val_rows.append(pred.cpu().numpy())
            true_val_rows.append(true_abs)
        val_loss = val_diff2 / max(val_mask, 1.0)
        pred_val = np.concatenate(pred_val_rows, axis=0)
        true_val = np.concatenate(true_val_rows, axis=0)

    pairs: list[VerificationPair] = []
    for si, sw in enumerate(val_windows):
        for li, lead_hours in enumerate(DEFAULT_LEADS):
            if not sw.mask[li]:
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
    return model, train_loss, val_loss, val_metrics, (env_mean, env_std)


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
) -> tuple[object, float, float, MetricSet, tuple]:
    """PINN analog of `real_run.train_lstm_stage`. Loss is masked
    track/intensity MSE (absolute-coordinate space) plus a small weighted
    `models.pinn.physics_residuals` penalty over the leads it's valid for
    (see module docstring). Also returns ``(env_mean, env_std)`` -- the
    environment vector's standardisation stats, needed to correctly
    reproduce this exact model's input space later (`training
    .real_latents`)."""
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
    return model, train_loss, val_loss, val_metrics, (env_mean, env_std)


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
    streaming: bool = False,
    batch_size: int = 32,
    num_workers: int = 0,
) -> tuple[CurriculumRun, MetricSet, RunArtifacts]:
    """Run the real Stage A -> Stage B curriculum for the PINN baseline.
    A fresh candidate-generator LSTM is trained per stage (see module
    docstring) on that stage's own train tracks before PINN is trained
    against its output.

    The returned ``RunArtifacts`` carries TWO trained models -- the Stage B
    ``PhysicsCorrector`` (``.model``) and the Stage B candidate-generator
    LSTM it corrects (``.candidate_model``), since `models.pinn
    .PhysicsCorrector.encode` needs both (`encode(environment, candidate)`)
    and the candidate LSTM is never persisted to checkpoint storage (module
    docstring) -- plus the environment vector's standardisation stats
    (``.env_mean``/``.env_std``). See `real_run.run_lstm_curriculum`'s
    docstring for why a ``RunArtifacts`` is returned at all (#22, `training
    .real_latents`).

    ``streaming=True`` uses `_train_candidate_lstm_streaming` and
    `train_pinn_stage_streaming` instead of the default full-batch pair
    (`docs/streaming_dataloader.md`) -- the last of the five models that
    doc scopes; PINN's candidate-generator LSTM has the same full-batch
    OOM shape one level removed, so it's streamed too, not just the outer
    PINN stage. ``num_workers`` (streaming only, default 0) forwards to
    `streaming.make_dataloader` -- see that function's docstring.
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

        if streaming:
            candidate_model = _train_candidate_lstm_streaming(
                train_tracks, rng, n_augment=n_augment, device=device,
                hidden_dim=candidate_hidden_dim, batch_size=batch_size, num_workers=num_workers,
            )
        else:
            candidate_model = _train_candidate_lstm(
                train_tracks, rng, n_augment=n_augment, device=device,
                hidden_dim=candidate_hidden_dim,
            )

        if model is None:
            model, _spec = build_pinn(
                input_dim=len(FEATURE_NAMES), hidden_dim=hidden_dim, lead_hours=DEFAULT_LEADS,
            )

        stage_fn = train_pinn_stage_streaming if streaming else train_pinn_stage
        stage_kwargs = {"batch_size": batch_size, "num_workers": num_workers} if streaming else {}
        model, train_loss, val_loss, val_metrics, env_stats = stage_fn(
            model, candidate_model, stage, train_tracks, val_tracks, cache_dir, rng,
            n_augment=n_augment, device=device, **stage_kwargs,
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
    env_mean, env_std = env_stats
    artifacts = RunArtifacts(
        model=model, candidate_model=candidate_model, env_mean=env_mean, env_std=env_std,
    )
    return run, val_metrics, artifacts
