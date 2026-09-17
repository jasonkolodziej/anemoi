"""Real latent extraction from the five trained Group 1 Stage B models
(#22, §5.7).

Anemoi-Spread (diffusion) and the fusion consensus model are conditioned on
latents pulled from the Group 1 models' ``.encode()`` -- the hook every
``models.*`` build function exposes for exactly this
(``models.base.ModelSpec``'s docstring: "carried alongside every model so
the fusion layer and the latent extractor can be written against the
contract rather than against each architecture"). This module is that
latent extractor.

It runs against the trained model objects held in memory by
``training.real_orchestrator.RealOrchestratorRunner`` for the SAME
schedule run -- not against checkpoints reloaded from durable storage,
since ``tracking.registry.ModelVersion`` doesn't record a checkpoint_uri
today, and PINN's candidate-generator LSTM (``real_run_pinn
._train_candidate_lstm``) is never persisted at all. Each
``training.real_run.RunArtifacts`` also carries the EXACT standardisation
stats Stage B fit its inputs/targets with, so a model's raw output can be
correctly un-standardised back to real displacement/wind units here --
refitting those stats independently would only approximate the real
inverse of what the model's output space actually is.

Each Group 1 model reads a different real representation of the same
window (track sequence, gridded channel stack, graph, environment +
candidate) -- what's common across all five, because
``real_run.iter_stage_windows`` derives it purely from the tracks and not
from any model-specific input, is the target ``(y, mask, base_lat,
base_lon)``. This module builds every model's representation from the SAME
window in one pass, so no separate join-by-identity step is needed: a
window that lacks a cached ``GriddedFields`` file (needed by
CNN/Transformer/GNN/PINN) is simply skipped for all five at once, exactly
like each per-model builder already skips it on its own.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..data.besttrack import Track
from ..data.gridded_cache import FetchTask, cache_path, load_cached_fields
from ..data.sources import Flavor
from ..data.splits import Split, assign_splits, filter_tracks
from ..data.storm_relative import displacement_nm, storm_relative_sequence
from ..models.base import DEFAULT_LEADS, require_torch
from .device import get_device
from .real_run import (
    RunArtifacts,
    boundaries_for_flavor,
    displacement_to_latlon,
    iter_stage_windows,
)

#: Order every per-window latent/prediction is concatenated/stacked in.
GROUP1_ORDER: tuple[str, ...] = ("lstm", "cnn", "transformer", "gnn", "pinn")

#: Real synoptic context features for the fusion consensus layer's
#: `models.fusion.build_fusion`'s ``context`` argument -- "conditioned on
#: the synoptic situation" per that module's docstring. All derived
#: directly from the window's own track data (no gridded cache needed),
#: so context is available for every window a Group 1 model built latents
#: for, never fabricated or looked up from an unrelated source.
CONTEXT_FEATURE_NAMES: tuple[str, ...] = (
    "lat_norm", "lon_norm", "wind_norm", "pressure_deficit_norm",
    "heading_sin", "heading_cos", "speed_norm", "wind_trend_norm",
    "day_of_year_sin", "day_of_year_cos",
)


@dataclass(frozen=True, slots=True)
class JointLatentSamples:
    """One row per real window every one of the five Group 1 models could
    build a real representation for.

    ``z`` is the concatenation of each model's ``.encode()`` output, in
    `GROUP1_ORDER` -- Anemoi-Spread's real conditioning vector. ``predictions``
    is each model's own real Stage B forecast, converted to a shared
    absolute (lat, lon, wind) space -- the fusion consensus layer's real
    per-model input. ``latent_dims`` records the per-model widths that sum
    to ``z.shape[-1]`` (a model's own ``ModelSpec.latent_dim``, whatever it
    happens to be -- not a fixed constant).
    """

    z: np.ndarray  # (N, sum(latent_dims))
    y: np.ndarray  # (N, n_leads, 3) -- masked multi-lead displacement targets
    mask: np.ndarray  # (N, n_leads)
    base_lat: np.ndarray  # (N,)
    base_lon: np.ndarray  # (N,)
    predictions: np.ndarray  # (N, 5, n_leads, 3) -- absolute (lat, lon, wind), GROUP1_ORDER
    true_absolute: np.ndarray  # (N, n_leads, 3) -- absolute (lat, lon, wind)
    context: np.ndarray  # (N, len(CONTEXT_FEATURE_NAMES))
    latent_dims: tuple[int, ...]

    def __len__(self) -> int:
        return len(self.z)


@dataclass(frozen=True, slots=True)
class JointLatentBundle:
    """Train/val split of `JointLatentSamples`, storm-disjoint (the same
    `data.splits` assignment every other real runner uses) so
    diffusion/fusion training doesn't leak a storm's windows across both."""

    train: JointLatentSamples
    val: JointLatentSamples

    def __len__(self) -> int:
        return len(self.train) + len(self.val)


def _context_features(sw) -> np.ndarray:
    """`CONTEXT_FEATURE_NAMES`, computed from one `real_run.StageWindow`'s
    own track data."""
    prev, cur = sw.window[-2], sw.window[-1]
    dx, dy = displacement_nm(prev, cur)
    dt_hours = (cur.valid_time - prev.valid_time).total_seconds() / 3600.0
    heading = math.atan2(dx, dy)
    speed_kt = math.hypot(dx, dy) / dt_hours if dt_hours > 0 else 0.0
    day_of_year = cur.valid_time.timetuple().tm_yday
    day_angle = 2.0 * math.pi * day_of_year / 365.25

    return np.array(
        [
            cur.lat / 90.0,
            cur.lon / 180.0,
            cur.max_wind_kt / 100.0,
            (1013.0 - cur.min_pressure_mb) / 100.0,
            math.sin(heading),
            math.cos(heading),
            speed_kt / 50.0,
            (cur.max_wind_kt - sw.window[0].max_wind_kt) / 50.0,
            math.sin(day_angle),
            math.cos(day_angle),
        ],
        dtype=np.float32,
    )


def _empty_samples(latent_dims: tuple[int, ...]) -> JointLatentSamples:
    n_leads = len(DEFAULT_LEADS)
    return JointLatentSamples(
        z=np.empty((0, sum(latent_dims))),
        y=np.empty((0, n_leads, 3)),
        mask=np.empty((0, n_leads), dtype=bool),
        base_lat=np.empty((0,)),
        base_lon=np.empty((0,)),
        predictions=np.empty((0, len(GROUP1_ORDER), n_leads, 3)),
        true_absolute=np.empty((0, n_leads, 3)),
        context=np.empty((0, len(CONTEXT_FEATURE_NAMES))),
        latent_dims=latent_dims,
    )


def _extract_for_tracks(
    tracks: list[Track],
    trained_artifacts: dict[str, RunArtifacts],
    gdas_cache_dir: Path | str,
    rng: np.random.Generator,
    n_augment: int,
    device=None,
) -> JointLatentSamples:
    from ..data.features import compute_environment_features
    from .real_run_cnn import CNN_FIELD_NAMES
    from .real_run_gnn import _node_features, batch_graph, build_mesh_topology
    from .real_run_pinn import PinnStageSamples, _candidate_and_true_absolute
    from .real_run_transformer import GRID_SIZE, TRANSFORMER_FIELD_NAMES

    torch = require_torch()
    device = device or get_device()
    cache_dir = Path(gdas_cache_dir)

    lstm_a = trained_artifacts["lstm"]
    cnn_a = trained_artifacts["cnn"]
    transformer_a = trained_artifacts["transformer"]
    gnn_a = trained_artifacts["gnn"]
    pinn_a = trained_artifacts["pinn"]

    lstm_x_rows: list[np.ndarray] = []
    cnn_x_rows: list[np.ndarray] = []
    trf_x_rows: list[np.ndarray] = []
    gnn_x_rows: list[np.ndarray] = []
    env_rows: list[np.ndarray] = []
    cand_track_rows: list[np.ndarray] = []
    y_rows: list[np.ndarray] = []
    mask_rows: list[np.ndarray] = []
    base_lat_rows: list[float] = []
    base_lon_rows: list[float] = []
    context_rows: list[np.ndarray] = []

    topo = None
    shape: tuple[int, int] | None = None
    gh, gw = GRID_SIZE

    for sw in iter_stage_windows(tracks, rng, n_augment):
        task = FetchTask(
            storm_id=sw.storm_id, valid_time=sw.current.valid_time,
            lat=sw.current.lat, lon=sw.current.lon,
        )
        path = cache_path(cache_dir, task)
        if not path.exists():
            continue
        fields = load_cached_fields(path)
        field_shape = fields.shape
        if field_shape[0] < gh or field_shape[1] < gw:
            continue  # too small to trim to the transformer's grid -- skip rather than abort
        if shape is None:
            shape = field_shape
            topo = build_mesh_topology(shape)
        elif field_shape != shape:
            continue  # ragged cached field shape -- skip this one row, not the whole extraction

        lstm_x_rows.append(storm_relative_sequence(sw.window))
        cnn_x_rows.append(np.stack([getattr(fields, name) for name in CNN_FIELD_NAMES]))
        trf_stack = np.stack([getattr(fields, name) for name in TRANSFORMER_FIELD_NAMES])
        trf_x_rows.append(trf_stack[:, :gh, :gw])
        gnn_x_rows.append(_node_features(fields, topo))
        env_rows.append(compute_environment_features(fields).values)
        cand_track_rows.append(storm_relative_sequence(sw.window))
        y_rows.append(sw.y)
        mask_rows.append(sw.mask)
        base_lat_rows.append(sw.current.lat)
        base_lon_rows.append(sw.current.lon)
        context_rows.append(_context_features(sw))

    latent_dims = (
        lstm_a.model.norm.normalized_shape[0],
        cnn_a.model.project.out_features,
        transformer_a.model.norm.normalized_shape[0],
        gnn_a.model.embed.out_features,
        pinn_a.model.correction.in_features,
    )
    if not y_rows:
        return _empty_samples(latent_dims)

    y = np.stack(y_rows)
    mask = np.stack(mask_rows)
    base_lat = np.array(base_lat_rows)
    base_lon = np.array(base_lon_rows)
    context = np.stack(context_rows).astype(np.float32)

    def to_t(arr: np.ndarray) -> object:
        return torch.as_tensor(arr, dtype=torch.float32, device=device)

    latents: list[np.ndarray] = []
    preds_abs: list[np.ndarray] = []

    # --- LSTM ----------------------------------------------------------
    lstm_x = np.stack(lstm_x_rows)
    lstm_a.model.to(device).eval()
    with torch.no_grad():
        lx_z = to_t((lstm_x - lstm_a.x_mean) / lstm_a.x_std)
        latents.append(lstm_a.model.encode(lx_z).cpu().numpy())
        pred_z = lstm_a.model(lx_z).cpu().numpy() * lstm_a.y_std + lstm_a.y_mean
    preds_abs.append(_displacement_to_absolute(pred_z, base_lat, base_lon))

    # --- CNN -------------------------------------------------------------
    # Uses cnn_a's own Stage B x/y stats (not refit here) -- the exact
    # inverse of the space that model's weights were actually trained in.
    cnn_x = np.stack(cnn_x_rows)
    cnn_a.model.to(device).eval()
    with torch.no_grad():
        cx_z = to_t((cnn_x - cnn_a.x_mean) / cnn_a.x_std)
        latents.append(cnn_a.model.encode(cx_z).cpu().numpy())
        pred_z = cnn_a.model(cx_z).cpu().numpy() * cnn_a.y_std + cnn_a.y_mean
    preds_abs.append(_displacement_to_absolute(pred_z, base_lat, base_lon))

    # --- Transformer -------------------------------------------------------
    trf_x = np.stack(trf_x_rows)
    transformer_a.model.to(device).eval()
    with torch.no_grad():
        tx_z = to_t((trf_x - transformer_a.x_mean) / transformer_a.x_std)
        latents.append(transformer_a.model.encode(tx_z).cpu().numpy())
        pred_z, _regime = transformer_a.model(tx_z)
        pred_z = pred_z.cpu().numpy() * transformer_a.y_std + transformer_a.y_mean
    preds_abs.append(_displacement_to_absolute(pred_z, base_lat, base_lon))

    # --- GNN -----------------------------------------------------------
    gnn_x = np.stack(gnn_x_rows)
    gx_z = (gnn_x - gnn_a.x_mean) / gnn_a.x_std
    gnn_a.model.to(device).eval()
    with torch.no_grad():
        xf, ei, ea, ci = batch_graph(gx_z, topo)
        xf_t = to_t(xf)
        ei_t = torch.as_tensor(ei, dtype=torch.long, device=device)
        ea_t = to_t(ea)
        ci_t = torch.as_tensor(ci, dtype=torch.long, device=device)
        latents.append(gnn_a.model.encode(xf_t, ei_t, ea_t, center_index=ci_t).cpu().numpy())
        pred_z = gnn_a.model(xf_t, ei_t, ea_t, center_index=ci_t).cpu().numpy()
        pred_z = pred_z * gnn_a.y_std + gnn_a.y_mean
    preds_abs.append(_displacement_to_absolute(pred_z, base_lat, base_lon))

    # --- PINN ------------------------------------------------------------
    env = np.stack(env_rows)
    env_z = (env - pinn_a.env_mean) / pinn_a.env_std
    pinn_samples = PinnStageSamples(
        x_track=np.stack(cand_track_rows), environment=env, y=y, mask=mask,
        base_lat=base_lat, base_lon=base_lon,
    )
    pinn_a.candidate_model.to(device).eval()
    pinn_a.model.to(device).eval()
    with torch.no_grad():
        cand_abs, true_abs = _candidate_and_true_absolute(
            pinn_a.candidate_model, pinn_samples, device
        )
        env_z_t = to_t(env_z)
        cand_t = to_t(cand_abs)
        latents.append(pinn_a.model.encode(env_z_t, cand_t).cpu().numpy())
        pred_abs = pinn_a.model(env_z_t, cand_t).cpu().numpy()
    preds_abs.append(pred_abs)

    z = np.concatenate(latents, axis=-1)
    predictions = np.stack(preds_abs, axis=1)  # (N, 5, n_leads, 3)

    return JointLatentSamples(
        z=z, y=y, mask=mask, base_lat=base_lat, base_lon=base_lon,
        predictions=predictions, true_absolute=true_abs, context=context,
        latent_dims=latent_dims,
    )


def _displacement_to_absolute(
    disp: np.ndarray, base_lat: np.ndarray, base_lon: np.ndarray
) -> np.ndarray:
    """``disp`` is (N, n_leads, 3) = (dx_east_nm, dy_north_nm, wind_kt);
    returns (N, n_leads, 3) = (lat, lon, wind)."""
    out = np.zeros_like(disp)
    n, n_leads, _ = disp.shape
    for si in range(n):
        for li in range(n_leads):
            dx, dy, wind = disp[si, li]
            lat, lon = displacement_to_latlon(base_lat[si], base_lon[si], dx, dy)
            out[si, li] = [lat, lon, wind]
    return out


def extract_joint_latents(
    tracks: list[Track],
    trained_artifacts: dict[str, RunArtifacts],
    gdas_cache_dir: Path | str,
    *,
    seed: int = 20260806,
    n_augment: int = 1,
    device=None,
) -> JointLatentBundle:
    """Extract real per-window latents/predictions/context from the five
    trained Group 1 models, split train/val the same storm-disjoint way
    every other real runner splits (`real_run.boundaries_for_flavor`'s
    operational, GDAS_FINETUNE boundaries -- latents are only ever
    extracted from Stage B, operational-flavor models, §4.6.1). ``device``
    overrides `device.get_device`'s autodetection -- mainly so local
    development on Apple Silicon can force ``"cpu"``, sidestepping a real
    torch/MPS ``nn.LSTM`` platform bug ("Placeholder storage has not been
    allocated on MPS device") that CUDA (the real training VM) doesn't have.
    """
    missing = [m for m in GROUP1_ORDER if m not in trained_artifacts]
    if missing:
        raise ValueError(f"missing trained Group 1 model(s): {missing}")

    boundaries = boundaries_for_flavor(Flavor.GDAS_FINETUNE)
    assignment = assign_splits(tracks, boundaries)
    train_tracks = filter_tracks(tracks, assignment, Split.TRAIN)
    val_tracks = filter_tracks(tracks, assignment, Split.VAL)

    rng = np.random.default_rng(seed)
    train_samples = _extract_for_tracks(
        train_tracks, trained_artifacts, gdas_cache_dir, rng, n_augment, device=device,
    )
    val_samples = _extract_for_tracks(
        val_tracks, trained_artifacts, gdas_cache_dir, rng, 1, device=device,
    )
    return JointLatentBundle(train=train_samples, val=val_samples)
