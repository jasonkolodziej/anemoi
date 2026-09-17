"""Real Stage A/B curriculum run for the LSTM baseline, against real HURDAT2
tracks (#22).

Scope of this first real runner: **LSTM only**. `models.lstm.build_lstm`'s
docstring is explicit that this architecture's input is storm-history
sequences, not gridded imagery -- it never reads ERA5/GDAS pixels -- so it is
the one Group 1 model that can run a genuinely real Stage A/B curriculum
today without waiting on `data.era5_cache`/`data.gdas_cache` to finish
backfilling. CNN (imagery), Transformer (gridded fields), GNN (graph
construction) and PINN (environment vector) each need their own real
data-loading design against the cached `GriddedFields`; this module doesn't
attempt to generalise to them yet.

Builds directly on two already-proven, tested pieces: `capacity_ablation`'s
windowing/standardisation pattern (real torch training against real tracks,
just generalised here from one fixed 6h-ahead proxy step to the real
multi-lead-time targets `models.base.DEFAULT_LEADS` -- what
`training.promotion`'s thresholds and `metrics.track.verify` actually need),
and `data.splits.STAGE_B_BOUNDARIES` (#22's split-boundary fix: GDAS's real
archive doesn't overlap `DEFAULT_BOUNDARIES`' train window at all).
"""

from __future__ import annotations

import math
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from ..data.besttrack import Track, WorkingTrackNoise, augment_track
from ..data.sources import Flavor
from ..data.splits import (
    DEFAULT_BOUNDARIES,
    STAGE_B_BOUNDARIES,
    Split,
    assign_splits,
    filter_tracks,
)
from ..data.storm_relative import STORM_RELATIVE_COLUMNS, displacement_nm, storm_relative_sequence
from ..geo import offset_position
from ..metrics.track import ForecastPoint, VerificationPair, to_metric_dict, verify
from ..models.base import DEFAULT_LEADS, require_torch
from ..tracking.checkpoint_store import CheckpointStore
from .capacity_ablation import SEQUENCE_LENGTH
from .curriculum import Curriculum, CurriculumRun, StageResult, StageSpec
from .device import get_device
from .promotion import MetricSet

#: Fixes-ahead for each of DEFAULT_LEADS, at the 6-hourly synoptic cadence.
LEAD_STEPS: tuple[int, ...] = tuple(h // 6 for h in DEFAULT_LEADS)
_MAX_LEAD_STEPS = LEAD_STEPS[-1]


def boundaries_for_flavor(flavor: Flavor) -> dict[Split, tuple[int, int]]:
    """Which `data.splits` boundary scheme a stage's real data comes from.

    Mirrors `cli.cmd_era5_cache`/`cmd_gdas_cache`'s choice: ERA5_PRETRAIN
    uses the default (decades-deep) window, GDAS_FINETUNE uses
    STAGE_B_BOUNDARIES (GDAS's real archive has zero overlap with the
    default train window -- see that constant's docstring).
    """
    return STAGE_B_BOUNDARIES if flavor is Flavor.GDAS_FINETUNE else DEFAULT_BOUNDARIES


def displacement_to_latlon(
    base_lat: float, base_lon: float, dx_east_nm: float, dy_north_nm: float
) -> tuple[float, float]:
    """Inverse of `storm_relative.displacement_nm`: recover an absolute
    position from an (east, north) displacement in nm."""
    distance_nm = math.hypot(dx_east_nm, dy_north_nm)
    if distance_nm < 1e-9:
        return base_lat, base_lon
    bearing = math.degrees(math.atan2(dx_east_nm, dy_north_nm)) % 360.0
    return offset_position(base_lat, base_lon, distance_nm, bearing)


@dataclass(frozen=True, slots=True)
class StageSamples:
    """Multi-lead-time training samples for the LSTM baseline.

    ``y``/``mask`` are shaped ``(N, len(DEFAULT_LEADS), 3)`` /
    ``(N, len(DEFAULT_LEADS))`` -- not every sample has every lead available
    (a storm's track can end before a 120h-ahead fix exists), so unavailable
    leads are zero-filled and masked out rather than synthesised or dropped
    whole-sample. ``base_lat``/``base_lon`` are the window's current fix,
    needed to turn a predicted or true displacement back into an absolute
    position for verification.
    """

    x: np.ndarray
    y: np.ndarray
    mask: np.ndarray
    base_lat: np.ndarray
    base_lon: np.ndarray

    def __len__(self) -> int:
        return len(self.x)


@dataclass(frozen=True, slots=True)
class RunArtifacts:
    """Everything beyond ``(CurriculumRun, MetricSet)`` that
    `training.real_latents.extract_joint_latents` needs from a completed
    Stage B run: the trained model, and the EXACT standardisation stats
    Stage B fit its inputs/targets with. Neither is recoverable any other
    way -- `tracking.registry.ModelVersion` doesn't record a checkpoint_uri
    (so the model can't just be reloaded), and the z-score stats are local
    variables inside `train_lstm_stage`/its per-model siblings, never
    returned anywhere else. Re-fitting them independently later (e.g. from
    the same tracks with a fresh RNG draw) would only approximate the real
    ones the model was actually trained against -- close, but not the
    exact inverse of what the model's output space actually is.
    """

    model: object
    #: LSTM/CNN/Transformer/GNN only: the single input tensor's and the
    #: (dx_east_nm, dy_north_nm, wind_kt) target's standardisation stats.
    #: None for PINN, whose inputs are a differently-shaped
    #: (environment, candidate) pair rather than one ``x`` -- see
    #: ``env_mean``/``env_std``/``candidate_model`` below instead.
    x_mean: np.ndarray | None = None
    x_std: np.ndarray | None = None
    y_mean: np.ndarray | None = None
    y_std: np.ndarray | None = None
    #: PINN only (`real_run_pinn`): its Stage B candidate-generator LSTM,
    #: plus the environment vector's standardisation stats. None for every
    #: other model, which don't have a second model or an environment
    #: vector to standardise. PINN's own output is already absolute
    #: (lat, lon, wind), so it needs no y_mean/y_std to un-standardise.
    candidate_model: object | None = None
    env_mean: np.ndarray | None = None
    env_std: np.ndarray | None = None


@dataclass(frozen=True, slots=True)
class StageWindow:
    """One training window's track-derived pieces, common to every model's
    real Stage A/B runner regardless of what ``x`` representation (track
    sequence, gridded channel stack, graph, environment vector...) gets
    built from it.

    ``window`` is ``SEQUENCE_LENGTH + 1`` working-quality fixes ending at
    ``current``; ``y``/``mask`` are the same masked multi-lead targets
    `build_stage_samples` (LSTM) uses, described there.
    """

    storm_id: str
    window: tuple
    current: object
    y: np.ndarray
    mask: np.ndarray


def iter_stage_windows(
    tracks: list[Track],
    rng: np.random.Generator,
    n_augment: int = 1,
    noise: WorkingTrackNoise | None = None,
):
    """Yield one `StageWindow` per (storm, augmented working-track, window)
    triple -- the shared windowing/target-construction loop every real
    per-model sample builder (LSTM's `build_stage_samples`, and the
    CNN/Transformer/GNN/PINN builders alongside it) is built on, so the
    "which fixes form a window, which leads are real" logic exists once.
    """
    n_leads = len(LEAD_STEPS)
    for final in tracks:
        if len(final.fixes) < SEQUENCE_LENGTH + 1 + LEAD_STEPS[0]:
            continue
        for working in augment_track(final, rng, n_variants=n_augment, noise=noise):
            for i in range(len(working.fixes) - SEQUENCE_LENGTH):
                window = working.fixes[i : i + SEQUENCE_LENGTH + 1]
                current = window[-1]
                current_idx = i + SEQUENCE_LENGTH

                y = np.zeros((n_leads, 3))
                mask = np.zeros(n_leads, dtype=bool)
                for li, step in enumerate(LEAD_STEPS):
                    target_idx = current_idx + step
                    if target_idx >= len(final.fixes):
                        continue
                    target = final.fixes[target_idx]
                    dx, dy = displacement_nm(current, target)
                    y[li] = [dx, dy, target.max_wind_kt]
                    mask[li] = True

                if not mask.any():
                    continue
                yield StageWindow(
                    storm_id=final.storm_id, window=window, current=current, y=y, mask=mask
                )


def build_stage_samples(
    tracks: list[Track],
    rng: np.random.Generator,
    n_augment: int = 1,
    noise: WorkingTrackNoise | None = None,
) -> StageSamples:
    """Generalises `capacity_ablation.build_samples` from one fixed 6h-ahead
    proxy step to real multi-lead targets (`DEFAULT_LEADS`, 12-120h) -- what
    `training.promotion.evaluate_promotion`'s thresholds actually need
    (track_error_48h_nm and friends). Input is always working-quality,
    labels always final-quality (Stage B's policy, `besttrack` module).
    """
    n_leads = len(LEAD_STEPS)
    x_rows: list[np.ndarray] = []
    y_rows: list[np.ndarray] = []
    mask_rows: list[np.ndarray] = []
    base_lat_rows: list[float] = []
    base_lon_rows: list[float] = []

    for sw in iter_stage_windows(tracks, rng, n_augment, noise):
        x_rows.append(storm_relative_sequence(sw.window))
        y_rows.append(sw.y)
        mask_rows.append(sw.mask)
        base_lat_rows.append(sw.current.lat)
        base_lon_rows.append(sw.current.lon)

    if not x_rows:
        return StageSamples(
            x=np.empty((0, SEQUENCE_LENGTH, len(STORM_RELATIVE_COLUMNS))),
            y=np.empty((0, n_leads, 3)),
            mask=np.empty((0, n_leads), dtype=bool),
            base_lat=np.empty((0,)),
            base_lon=np.empty((0,)),
        )
    return StageSamples(
        x=np.stack(x_rows),
        y=np.stack(y_rows),
        mask=np.stack(mask_rows),
        base_lat=np.array(base_lat_rows),
        base_lon=np.array(base_lon_rows),
    )


def _standardize_x(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = x.mean(axis=(0, 1))
    std = x.std(axis=(0, 1))
    std[std < 1e-8] = 1.0
    return (x - mean) / std, mean, std


def _standardize_y(y: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per-lead, per-channel mean/std, fit only over masked-valid entries --
    displacement scale at 12h and 120h differ by roughly an order of
    magnitude, so one shared scale factor across leads would bias training
    toward the longer, larger-magnitude leads."""
    n_leads = y.shape[1]
    mean = np.zeros((n_leads, 3))
    std = np.ones((n_leads, 3))
    for li in range(n_leads):
        valid = mask[:, li]
        if valid.any():
            vals = y[valid, li, :]
            mean[li] = vals.mean(axis=0)
            s = vals.std(axis=0)
            s[s < 1e-8] = 1.0
            std[li] = s
    return mean, std


def freeze_encoder(model, frozen_modules: tuple[str, ...]) -> None:
    """LSTM-specific: 'encoder' means every parameter outside `.head`
    (the `.rnn` + `.norm` submodules `TrackRNN.encode` uses). No
    generalised per-architecture freezing contract exists yet -- add one
    when CNN/Transformer/GNN/PINN get real training loops."""
    if "encoder" not in frozen_modules:
        return
    for name, param in model.named_parameters():
        if not name.startswith("head."):
            param.requires_grad = False


def train_lstm_stage(
    model,
    stage: StageSpec,
    train_tracks: list[Track],
    val_tracks: list[Track],
    rng: np.random.Generator,
    *,
    n_augment: int = 3,
    device=None,
) -> tuple[object, float, float, MetricSet, tuple]:
    """Train ``model`` (fresh, or Stage A's trained weights for Stage B)
    through one curriculum stage against real tracks.

    Full-batch, matching `capacity_ablation.train_cell`'s proven pattern --
    same training shape, generalised to masked multi-lead targets and
    ``stage.frozen_modules``. Returns ``(model, train_loss, val_loss,
    val_metrics, standardization_stats)``: the two losses are masked MSE in
    standardised space (comparable across stages), ``val_metrics`` carries
    the real nm/kt breakdown `training.promotion.evaluate_promotion` needs,
    and ``standardization_stats`` is ``(x_mean, x_std, y_mean, y_std)`` --
    this stage's exact fit, needed to correctly un-standardise this model's
    output later (`training.real_latents`).
    """
    if not train_tracks or not val_tracks:
        raise ValueError(f"stage {stage.name}: empty train or val storm set")

    torch = require_torch()
    device = device or get_device()

    train_samples = build_stage_samples(train_tracks, rng, n_augment=n_augment)
    val_samples = build_stage_samples(val_tracks, rng, n_augment=1)
    if len(train_samples) == 0 or len(val_samples) == 0:
        raise ValueError(f"stage {stage.name}: no usable samples built from the given tracks")

    x_train, x_mean, x_std = _standardize_x(train_samples.x)
    y_mean, y_std = _standardize_y(train_samples.y, train_samples.mask)
    x_val = (val_samples.x - x_mean) / x_std
    y_train_z = (train_samples.y - y_mean) / y_std
    y_val_z = (val_samples.y - y_mean) / y_std  # standardised with TRAIN stats only

    freeze_encoder(model, stage.frozen_modules)
    model.to(device)

    def masked_mse(pred, target, mask3) -> object:
        diff2 = (pred - target) ** 2 * mask3
        return diff2.sum() / mask3.sum().clamp(min=1.0)

    xt = torch.as_tensor(x_train, dtype=torch.float32, device=device)
    yt = torch.as_tensor(y_train_z, dtype=torch.float32, device=device)
    mt = torch.as_tensor(train_samples.mask, dtype=torch.float32, device=device).unsqueeze(-1)

    trainable = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.Adam(trainable, lr=stage.learning_rate)

    model.train()
    for _ in range(stage.epochs):
        opt.zero_grad()
        loss = masked_mse(model(xt), yt, mt)
        loss.backward()
        opt.step()

    model.eval()
    with torch.no_grad():
        train_loss = float(masked_mse(model(xt), yt, mt).item())

        xv = torch.as_tensor(x_val, dtype=torch.float32, device=device)
        yv = torch.as_tensor(y_val_z, dtype=torch.float32, device=device)
        mv = torch.as_tensor(val_samples.mask, dtype=torch.float32, device=device).unsqueeze(-1)
        pred_val_z = model(xv)
        val_loss = float(masked_mse(pred_val_z, yv, mv).item())
        pred_val = pred_val_z.cpu().numpy() * y_std + y_mean

    pairs: list[VerificationPair] = []
    for si in range(len(val_samples)):
        base_lat, base_lon = val_samples.base_lat[si], val_samples.base_lon[si]
        for li, lead_hours in enumerate(DEFAULT_LEADS):
            if not val_samples.mask[si, li]:
                continue
            pred_dx, pred_dy, pred_wind = pred_val[si, li]
            pred_lat, pred_lon = displacement_to_latlon(base_lat, base_lon, pred_dx, pred_dy)
            obs_dx, obs_dy, obs_wind = val_samples.y[si, li]
            obs_lat, obs_lon = displacement_to_latlon(base_lat, base_lon, obs_dx, obs_dy)
            pairs.append(
                VerificationPair(
                    forecast=ForecastPoint(
                        lead_hours=lead_hours, lat=pred_lat, lon=pred_lon,
                        max_wind_kt=float(pred_wind),
                    ),
                    obs_lat=obs_lat,
                    obs_lon=obs_lon,
                    obs_wind_kt=float(obs_wind),
                )
            )

    if not pairs:
        raise ValueError(f"stage {stage.name}: no verifiable (lead, sample) pairs in val")
    val_metrics = MetricSet(split="val", flavor=stage.flavor, values=to_metric_dict(verify(pairs)))
    return model, train_loss, val_loss, val_metrics, (x_mean, x_std, y_mean, y_std)


def train_lstm_stage_streaming(
    model,
    stage: StageSpec,
    train_tracks: list[Track],
    val_tracks: list[Track],
    rng: np.random.Generator,
    *,
    n_augment: int = 3,
    batch_size: int = 64,
    num_workers: int = 0,
    device=None,
) -> tuple[object, float, float, MetricSet, tuple]:
    """`train_lstm_stage`'s streaming analog (`docs/streaming_dataloader.md`) --
    same return contract, same masked multi-lead loss and verification
    shape, but real per-batch training via a `torch.utils.data.DataLoader`
    instead of one full-dataset GPU tensor, and online (Welford/Chan)
    standardisation statistics instead of one `.mean()`/`.std()` call over
    a fully-materialized array. Per-step VRAM is now `O(batch_size)`, not
    `O(dataset size)` -- see that doc for why the full-batch version can't
    just be run on a bigger GPU as a durable fix.

    Windows themselves (`real_run.StageWindow`, from `iter_stage_windows`)
    are still fully listed in memory -- cheap, since each is a handful of
    `Fix` objects plus small arrays, not the real per-window track data.
    """
    from .streaming import OnlineMaskedLeadMeanStd, OnlineMeanStd, WindowDataset, make_dataloader

    if not train_tracks or not val_tracks:
        raise ValueError(f"stage {stage.name}: empty train or val storm set")

    torch = require_torch()
    device = device or get_device()

    train_windows = list(iter_stage_windows(train_tracks, rng, n_augment))
    val_windows = list(iter_stage_windows(val_tracks, rng, 1))
    if not train_windows or not val_windows:
        raise ValueError(f"stage {stage.name}: no usable samples built from the given tracks")

    def build_x(sw):
        return storm_relative_sequence(sw.window)

    n_leads = len(LEAD_STEPS)
    raw_train_ds = WindowDataset(train_windows, build_x)
    x_acc = OnlineMeanStd(reduce_axes=(0, 1))
    y_acc = OnlineMaskedLeadMeanStd(n_leads=n_leads)
    for i in range(len(raw_train_ds)):
        x, y, mask = raw_train_ds[i]
        x_acc.update(x[None])
        y_acc.update(y[None], mask[None].astype(bool))
    x_mean, x_std = x_acc.finalize()
    y_mean, y_std = y_acc.finalize()

    train_ds = WindowDataset(
        train_windows, build_x, x_mean=x_mean, x_std=x_std, y_mean=y_mean, y_std=y_std,
    )
    val_ds = WindowDataset(
        val_windows, build_x, x_mean=x_mean, x_std=x_std, y_mean=y_mean, y_std=y_std,
    )
    train_loader = make_dataloader(
        train_ds, batch_size=batch_size, shuffle=True, num_workers=num_workers,
    )
    val_loader = make_dataloader(
        val_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers,
    )

    freeze_encoder(model, stage.frozen_modules)
    model.to(device)

    def masked_mse_sums(pred, target, mask3) -> tuple[object, object]:
        diff2 = (pred - target) ** 2 * mask3
        return diff2.sum(), mask3.sum()

    trainable = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.Adam(trainable, lr=stage.learning_rate)

    model.train()
    for _ in range(stage.epochs):
        for xb, yb, mb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            mb = mb.to(device).unsqueeze(-1)
            opt.zero_grad()
            diff2_sum, mask_sum = masked_mse_sums(model(xb), yb, mb)
            loss = diff2_sum / mask_sum.clamp(min=1.0)
            loss.backward()
            opt.step()

    model.eval()
    with torch.no_grad():
        train_diff2, train_mask = 0.0, 0.0
        for xb, yb, mb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            mb = mb.to(device).unsqueeze(-1)
            d, m = masked_mse_sums(model(xb), yb, mb)
            train_diff2 += float(d.item())
            train_mask += float(m.item())
        train_loss = train_diff2 / max(train_mask, 1.0)

        val_diff2, val_mask = 0.0, 0.0
        pred_val_rows: list[np.ndarray] = []
        for xb, yb, mb in val_loader:
            xb, yb = xb.to(device), yb.to(device)
            mb3 = mb.to(device).unsqueeze(-1)
            pred = model(xb)
            d, m = masked_mse_sums(pred, yb, mb3)
            val_diff2 += float(d.item())
            val_mask += float(m.item())
            pred_val_rows.append(pred.cpu().numpy())
        val_loss = val_diff2 / max(val_mask, 1.0)
        pred_val = np.concatenate(pred_val_rows, axis=0) * y_std + y_mean

    pairs: list[VerificationPair] = []
    for si, sw in enumerate(val_windows):
        base_lat, base_lon = sw.current.lat, sw.current.lon
        for li, lead_hours in enumerate(DEFAULT_LEADS):
            if not sw.mask[li]:
                continue
            pred_dx, pred_dy, pred_wind = pred_val[si, li]
            pred_lat, pred_lon = displacement_to_latlon(base_lat, base_lon, pred_dx, pred_dy)
            obs_dx, obs_dy, obs_wind = sw.y[li]
            obs_lat, obs_lon = displacement_to_latlon(base_lat, base_lon, obs_dx, obs_dy)
            pairs.append(
                VerificationPair(
                    forecast=ForecastPoint(
                        lead_hours=lead_hours, lat=pred_lat, lon=pred_lon,
                        max_wind_kt=float(pred_wind),
                    ),
                    obs_lat=obs_lat,
                    obs_lon=obs_lon,
                    obs_wind_kt=float(obs_wind),
                )
            )

    if not pairs:
        raise ValueError(f"stage {stage.name}: no verifiable (lead, sample) pairs in val")
    val_metrics = MetricSet(split="val", flavor=stage.flavor, values=to_metric_dict(verify(pairs)))
    return model, train_loss, val_loss, val_metrics, (x_mean, x_std, y_mean, y_std)


def run_lstm_curriculum(
    tracks: list[Track],
    checkpoint_store: CheckpointStore,
    *,
    seed: int = 20260806,
    n_augment: int = 3,
    hidden_dim: int = 128,
    curriculum_kwargs: dict | None = None,
    streaming: bool = False,
    batch_size: int = 64,
    num_workers: int = 0,
) -> tuple[CurriculumRun, MetricSet, RunArtifacts]:
    """Run the real Stage A -> Stage B curriculum for the LSTM baseline
    against real HURDAT2 tracks, uploading each stage's checkpoint to
    durable storage.

    ``hidden_dim`` defaults to 128: the #9 capacity ablation's GO decision
    (`docs/capacity_ablation.md`) -- validation loss kept improving through
    hidden_dim=128 with no sign of flattening, so this is the largest
    capacity that ablation actually measured, not an arbitrary choice.
    Returns the completed ``CurriculumRun``, Stage B's (the deployable
    stage's) validation ``MetricSet`` (ready for
    ``training.promotion.evaluate_promotion``), and a ``RunArtifacts``
    bundling the trained Stage B model with its standardisation stats --
    needed by ``training.real_latents`` to extract real Anemoi-Spread/fusion
    conditioning latents and un-standardised predictions (#22, §5.7).

    ``streaming=True`` uses `train_lstm_stage_streaming` instead of the
    default full-batch `train_lstm_stage` -- real per-batch training with
    online standardisation statistics, `O(batch_size)` VRAM instead of
    `O(dataset size)` (`docs/streaming_dataloader.md`). Off by default:
    the full-batch path is simpler and fine at small real scale; opt in
    once the cached dataset is large enough that full-batch risks OOM.

    ``num_workers`` (streaming only, default 0) forwards to
    `streaming.make_dataloader` -- real DataLoader worker processes that
    overlap batch loading with GPU compute instead of blocking the
    training step on it. See that function's docstring for why it forces
    ``fork`` explicitly and defaults to 0.
    """
    from ..models.lstm import build_lstm

    require_torch()
    rng = np.random.default_rng(seed)
    curriculum = Curriculum.standard("lstm", **(curriculum_kwargs or {}))
    run = CurriculumRun(curriculum=curriculum)

    model = None
    val_metrics: MetricSet | None = None
    for stage in curriculum.stages:
        boundaries = boundaries_for_flavor(stage.flavor)
        assignment = assign_splits(tracks, boundaries)
        train_tracks = filter_tracks(tracks, assignment, Split.TRAIN)
        val_tracks = filter_tracks(tracks, assignment, Split.VAL)

        if model is None:
            model, _spec = build_lstm(
                input_dim=len(STORM_RELATIVE_COLUMNS), hidden_dim=hidden_dim,
                lead_hours=DEFAULT_LEADS,
            )

        stage_fn = train_lstm_stage_streaming if streaming else train_lstm_stage
        stage_kwargs = {"batch_size": batch_size, "num_workers": num_workers} if streaming else {}
        model, train_loss, val_loss, val_metrics, stats = stage_fn(
            model, stage, train_tracks, val_tracks, rng, n_augment=n_augment, **stage_kwargs,
        )

        torch = require_torch()
        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = Path(tmpdir) / f"{stage.name}.pt"
            torch.save(model.state_dict(), local_path)
            key = f"checkpoints/lstm/{stage.name}/{datetime.now(UTC):%Y%m%dT%H%M%S}.pt"
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

    assert val_metrics is not None  # curriculum always has >=1 stage
    x_mean, x_std, y_mean, y_std = stats
    artifacts = RunArtifacts(model=model, x_mean=x_mean, x_std=x_std, y_mean=y_mean, y_std=y_std)
    return run, val_metrics, artifacts
