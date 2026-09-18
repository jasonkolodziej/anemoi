"""Real Stage A/B curriculum run for the CNN baseline, against cached real
GriddedFields (#22).

Unlike the LSTM baseline (`training.real_run`, track-only), CNN's real input
is genuinely gridded: `models.cnn.build_cnn`'s docstring describes "GOES
imagery stacks", but the architecture itself just consumes any multi-channel
2-D image -- resolution-agnostic (global average pool at the end, per the
docstring), so it needs no fixed grid size. Real GOES crops aren't fetched
yet (PLAN.md's Satellite row), but the real ERA5/GDAS `GriddedFields` this
project already fetches and caches (`data.era5_cache`/`data.gdas_cache`) are
exactly the same shape of thing -- storm-centred, multi-channel, 2-D -- so
this runner feeds those in as the channel stack instead of waiting on real
satellite imagery. All 10 cached fields (u200, v200, u850, v850, z500,
rh700, t700, mslp, sst, ohc) are used as channels.

Training data is read from local cache directories
(`data.era5_cache`/`data.gdas_cache`'s `--cache-dir`), not fetched live --
this runner is meant to run after (or alongside) those. A fix without a
cached file yet is skipped, not an error: the cache jobs are resumable and
still filling in the background on a real run, so this runner trains on
however much is cached at the moment it's invoked.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from ..data.besttrack import Track, WorkingTrackNoise
from ..data.features import sanitize_field_pixels
from ..data.gridded_cache import FetchTask, cache_path, load_cached_fields
from ..data.sources import Flavor
from ..data.splits import Split, assign_splits, filter_tracks
from ..metrics.track import ForecastPoint, VerificationPair, to_metric_dict, verify
from ..models.base import DEFAULT_LEADS, require_torch
from ..tracking.checkpoint_store import CheckpointStore
from .curriculum import Curriculum, CurriculumRun, StageResult, StageSpec
from .device import get_device
from .promotion import MetricSet
from .real_run import (
    LEAD_STEPS,
    RunArtifacts,
    boundaries_for_flavor,
    displacement_to_latlon,
    freeze_encoder,
    iter_stage_windows,
)

#: Order the 10 cached GriddedFields arrays are stacked as CNN channels.
CNN_FIELD_NAMES: tuple[str, ...] = (
    "u200", "v200", "u850", "v850", "z500", "rh700", "t700", "mslp", "sst", "ohc",
)


def _sanitized_channel_stack(fields) -> np.ndarray | None:
    """The real `CNN_FIELD_NAMES` channel stack for one window's cached
    fields, with `data.features.sanitize_field_pixels` applied per channel
    -- ``None`` if any channel (real ERA5 ``sst``/``ohc`` are NaN over
    land) is entirely NaN, signalling the caller to skip this window (see
    `sanitize_field_pixels`'s own docstring for why this can't be left
    unhandled: a single NaN pixel reaching `training.streaming
    .OnlineMeanStd` corrupts standardization stats for the whole stage,
    not just this window)."""
    channels = []
    for name in CNN_FIELD_NAMES:
        sanitized = sanitize_field_pixels(getattr(fields, name))
        if sanitized is None:
            return None
        channels.append(sanitized)
    return np.stack(channels)


@dataclass(frozen=True, slots=True)
class CnnStageSamples:
    x: np.ndarray  # (N, len(CNN_FIELD_NAMES), H, W)
    y: np.ndarray
    mask: np.ndarray
    base_lat: np.ndarray
    base_lon: np.ndarray

    def __len__(self) -> int:
        return len(self.x)


def build_cnn_samples(
    tracks: list[Track],
    cache_dir: Path | str,
    rng: np.random.Generator,
    n_augment: int = 1,
    noise: WorkingTrackNoise | None = None,
) -> CnnStageSamples:
    """Same windows/targets as `real_run.build_stage_samples`, but ``x`` is
    the real cached `GriddedFields` channel stack for the window's current
    fix instead of a storm-relative track sequence. A fix with no cached
    file yet is skipped (see module docstring), so this can be re-run as
    more of the cache fills in without any special handling.
    """
    cache_dir = Path(cache_dir)
    x_rows: list[np.ndarray] = []
    y_rows: list[np.ndarray] = []
    mask_rows: list[np.ndarray] = []
    base_lat_rows: list[float] = []
    base_lon_rows: list[float] = []
    shape: tuple[int, int] | None = None

    for sw in iter_stage_windows(tracks, rng, n_augment, noise):
        task = FetchTask(
            storm_id=sw.storm_id, valid_time=sw.current.valid_time,
            lat=sw.current.lat, lon=sw.current.lon,
        )
        path = cache_path(cache_dir, task)
        if not path.exists():
            continue
        fields = load_cached_fields(path)
        stack = _sanitized_channel_stack(fields)
        if stack is None:
            continue
        if shape is None:
            shape = stack.shape[1:]
        elif stack.shape[1:] != shape:
            raise ValueError(
                f"ragged cached field shape for {sw.storm_id}: {stack.shape[1:]} != {shape} "
                "-- cache was built with inconsistent box_deg"
            )

        x_rows.append(stack)
        y_rows.append(sw.y)
        mask_rows.append(sw.mask)
        base_lat_rows.append(sw.current.lat)
        base_lon_rows.append(sw.current.lon)

    n_leads = len(LEAD_STEPS)
    if not x_rows:
        return CnnStageSamples(
            x=np.empty((0, len(CNN_FIELD_NAMES), 0, 0)),
            y=np.empty((0, n_leads, 3)),
            mask=np.empty((0, n_leads), dtype=bool),
            base_lat=np.empty((0,)),
            base_lon=np.empty((0,)),
        )
    return CnnStageSamples(
        x=np.stack(x_rows),
        y=np.stack(y_rows),
        mask=np.stack(mask_rows),
        base_lat=np.array(base_lat_rows),
        base_lon=np.array(base_lon_rows),
    )


def _standardize_cnn_x(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = x.mean(axis=(0, 2, 3), keepdims=True)
    std = x.std(axis=(0, 2, 3), keepdims=True)
    std[std < 1e-8] = 1.0
    return (x - mean) / std, mean, std


def _standardize_y(y: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
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


def train_cnn_stage(
    model,
    stage: StageSpec,
    train_tracks: list[Track],
    val_tracks: list[Track],
    cache_dir: Path | str,
    rng: np.random.Generator,
    *,
    n_augment: int = 3,
    device=None,
) -> tuple[object, float, float, MetricSet, tuple]:
    """CNN analog of `real_run.train_lstm_stage` -- same masked multi-lead
    training/verification shape, ``x`` built from cached real GriddedFields
    instead of track sequences. See that function for the loss/verification
    design this mirrors, including the extra ``(x_mean, x_std, y_mean,
    y_std)`` returned alongside the usual four values.
    """
    if not train_tracks or not val_tracks:
        raise ValueError(f"stage {stage.name}: empty train or val storm set")

    torch = require_torch()
    device = device or get_device()

    train_samples = build_cnn_samples(train_tracks, cache_dir, rng, n_augment=n_augment)
    val_samples = build_cnn_samples(val_tracks, cache_dir, rng, n_augment=1)
    if len(train_samples) == 0 or len(val_samples) == 0:
        raise ValueError(
            f"stage {stage.name}: no cached GriddedFields matched the given tracks in "
            f"{cache_dir} -- has data.era5_cache/data.gdas_cache fetched anything yet?"
        )

    x_train, x_mean, x_std = _standardize_cnn_x(train_samples.x)
    y_mean, y_std = _standardize_y(train_samples.y, train_samples.mask)
    x_val = (val_samples.x - x_mean) / x_std
    y_train_z = (train_samples.y - y_mean) / y_std
    y_val_z = (val_samples.y - y_mean) / y_std

    freeze_encoder(model, stage.frozen_modules)
    model.to(device)

    def masked_mse(pred, target, mask3):
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


def train_cnn_stage_streaming(
    model,
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
    """`train_cnn_stage`'s streaming analog (`docs/streaming_dataloader.md`) --
    same return contract, real per-batch training via a `torch.utils.data
    .DataLoader` and online standardisation statistics instead of one
    full-dataset GPU tensor. See `real_run.train_lstm_stage_streaming` for
    the reference implementation this follows. ``num_workers`` (default 0)
    forwards to `streaming.make_dataloader` -- see that function's
    docstring.
    """
    from .streaming import (
        OnlineMaskedLeadMeanStd,
        OnlineMeanStd,
        WindowDataset,
        filter_windows_with_cache,
        filter_windows_with_finite_fields,
        make_dataloader,
    )

    if not train_tracks or not val_tracks:
        raise ValueError(f"stage {stage.name}: empty train or val storm set")

    torch = require_torch()
    device = device or get_device()

    raw_train_windows = filter_windows_with_cache(
        list(iter_stage_windows(train_tracks, rng, n_augment)), cache_dir,
    )
    train_windows = filter_windows_with_finite_fields(raw_train_windows, cache_dir, CNN_FIELD_NAMES)
    raw_val_windows = filter_windows_with_cache(
        list(iter_stage_windows(val_tracks, rng, 1)), cache_dir,
    )
    val_windows = filter_windows_with_finite_fields(raw_val_windows, cache_dir, CNN_FIELD_NAMES)
    if not train_windows or not val_windows:
        raise ValueError(
            f"stage {stage.name}: no cached GriddedFields matched the given tracks in "
            f"{cache_dir} -- has data.era5_cache/data.gdas_cache fetched anything yet, or "
            "were every matched window's fields entirely NaN (storms entirely over land)?"
        )

    def build_x(sw):
        fields = load_cached_fields(cache_path(cache_dir, FetchTask(
            storm_id=sw.storm_id, valid_time=sw.current.valid_time,
            lat=sw.current.lat, lon=sw.current.lon,
        )))
        return _sanitized_channel_stack(fields)

    n_leads = len(LEAD_STEPS)
    raw_train_ds = WindowDataset(train_windows, build_x)
    x_acc = OnlineMeanStd(reduce_axes=(0, 2, 3), keepdims=True)
    y_acc = OnlineMaskedLeadMeanStd(n_leads=n_leads)
    for i in range(len(raw_train_ds)):
        x, y, mask = raw_train_ds[i]
        x_acc.update(x[None])
        y_acc.update(y[None], mask[None].astype(bool))
    x_mean, x_std = x_acc.finalize()
    y_mean, y_std = y_acc.finalize()
    # x_mean/x_std keep the (1, C, 1, 1) shape _standardize_cnn_x's callers
    # (e.g. real_latents.py) expect against a *batched* (N, C, H, W) array.
    # WindowDataset.__getitem__ standardizes one *unbatched* (C, H, W) item
    # at a time, so it needs the leading batch axis squeezed off here --
    # (10, 9, 9) broadcast against (1, 10, 1, 1) would otherwise pick up a
    # spurious leading 1 instead of matching per-channel.
    item_x_mean, item_x_std = x_mean[0], x_std[0]

    train_ds = WindowDataset(
        train_windows, build_x, x_mean=item_x_mean, x_std=item_x_std, y_mean=y_mean, y_std=y_std,
    )
    val_ds = WindowDataset(
        val_windows, build_x, x_mean=item_x_mean, x_std=item_x_std, y_mean=y_mean, y_std=y_std,
    )
    train_loader = make_dataloader(
        train_ds, batch_size=batch_size, shuffle=True, num_workers=num_workers,
    )
    val_loader = make_dataloader(
        val_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers,
    )

    freeze_encoder(model, stage.frozen_modules)
    model.to(device)

    def masked_mse_sums(pred, target, mask3):
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


def run_cnn_curriculum(
    tracks: list[Track],
    checkpoint_store: CheckpointStore,
    era5_cache_dir: Path | str,
    gdas_cache_dir: Path | str,
    *,
    seed: int = 20260806,
    n_augment: int = 3,
    latent_dim: int = 256,
    curriculum_kwargs: dict | None = None,
    streaming: bool = False,
    batch_size: int = 32,
    num_workers: int = 0,
) -> tuple[CurriculumRun, MetricSet, RunArtifacts]:
    """Run the real Stage A -> Stage B curriculum for the CNN baseline
    against real cached GriddedFields.

    Stage A reads from ``era5_cache_dir``, Stage B from ``gdas_cache_dir`` --
    matching `data.era5_cache`/`data.gdas_cache`'s own split (see
    `real_run.boundaries_for_flavor`). ``latent_dim`` defaults to the
    architecture's own default (256); the capacity ablation (#9) measured
    only the LSTM, so there's no measured recommendation to override it with
    yet. Also returns a ``RunArtifacts`` bundling the trained Stage B model
    with its standardisation stats (see `real_run.run_lstm_curriculum`'s
    docstring for why).

    ``streaming=True`` uses `train_cnn_stage_streaming` instead of the
    default full-batch `train_cnn_stage` -- real per-batch training,
    `O(batch_size)` VRAM instead of `O(dataset size)`
    (`docs/streaming_dataloader.md`; this is the model that actually hit a
    real CUDA OOM training full-batch against the real, growing cache).
    ``num_workers`` (streaming only, default 0) forwards to
    `streaming.make_dataloader` -- see that function's docstring.
    """
    from ..models.cnn import build_cnn

    require_torch()
    rng = np.random.default_rng(seed)
    curriculum = Curriculum.standard("cnn", **(curriculum_kwargs or {}))
    run = CurriculumRun(curriculum=curriculum)

    model = None
    val_metrics: MetricSet | None = None
    for stage in curriculum.stages:
        cache_dir = era5_cache_dir if stage.flavor is Flavor.ERA5_PRETRAIN else gdas_cache_dir
        boundaries = boundaries_for_flavor(stage.flavor)
        assignment = assign_splits(tracks, boundaries)
        train_tracks = filter_tracks(tracks, assignment, Split.TRAIN)
        val_tracks = filter_tracks(tracks, assignment, Split.VAL)

        if model is None:
            model, _spec = build_cnn(
                in_channels=len(CNN_FIELD_NAMES), latent_dim=latent_dim, lead_hours=DEFAULT_LEADS,
            )

        stage_fn = train_cnn_stage_streaming if streaming else train_cnn_stage
        stage_kwargs = {"batch_size": batch_size, "num_workers": num_workers} if streaming else {}
        model, train_loss, val_loss, val_metrics, stats = stage_fn(
            model, stage, train_tracks, val_tracks, cache_dir, rng,
            n_augment=n_augment, **stage_kwargs,
        )

        torch = require_torch()
        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = Path(tmpdir) / f"{stage.name}.pt"
            torch.save(model.state_dict(), local_path)
            key = f"checkpoints/cnn/{stage.name}/{datetime.now(UTC):%Y%m%dT%H%M%S}.pt"
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
    x_mean, x_std, y_mean, y_std = stats
    artifacts = RunArtifacts(model=model, x_mean=x_mean, x_std=x_std, y_mean=y_mean, y_std=y_std)
    return run, val_metrics, artifacts
