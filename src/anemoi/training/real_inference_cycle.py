"""Real `deterministic_fn` for `inference.cycle.run_cycle` (#78).

Built from LSTM/CNN/Transformer/GNN's real trained checkpoints
(`real_inference.load_trained_model`) and real live features
(`real_inference_live.build_live_<model>_x`), combined via the real
non-learned inverse-error consensus (`inference.cycle.fusion_weights`) --
not the learned `ConsensusFusion` model, which needs all five Group 1
predictions in a fixed order (``n_models=5``) to run at all. PINN's own
live feature builder needs its candidate model's forecast converted to
absolute coordinates first (a real, separate piece) and is deferred to
its own follow-up, the same way `real_inference_live` deferred it --
until then, the learned fusion model and the diffusion ensemble (both of
which also need all five real Group 1 predictions via `real_latents
.extract_joint_latents`) can't run correctly either. `fusion_weights`
is not a stopgap invented for this gap: it is already the system's real,
existing non-learned consensus path (§6.1, §10.1 divergence handling),
used here with real per-model validation error instead of a synthetic
one.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from ..data.besttrack import Fix, Track
    from ..inference.cycle import DeterministicForecast
    from ..inference.scheduler import CyclePlan
    from ..tracking.checkpoint_store import CheckpointStore
    from ..tracking.registry import ModelRegistry

#: A model with no real recorded validation error (shouldn't happen for
#: any version registered through the real training path, but a real
#: inference process must still degrade rather than crash) gets this
#: sentinel -- large enough that `fusion_weights`' inverse-error weighting
#: gives it only its floor share, not the outsized weight a small
#: fallback like 1.0 would (a real track_error_48h_nm is routinely in the
#: hundreds of nm; 1.0 would look like an implausibly *good* model and
#: dominate the consensus instead of being appropriately distrusted).
_UNKNOWN_ERROR_SENTINEL = 1e6

#: Group 1 models with a real live feature builder (`real_inference_live`)
#: -- PINN is deferred (module docstring).
_GROUP1_LIVE_MODELS: tuple[str, ...] = ("lstm", "cnn", "transformer", "gnn")


class InferenceCycleError(RuntimeError):
    pass


def _build_live_x(name: str, track: Track, current: Fix, cache_dir: Path | str):
    from .real_inference_live import (
        build_live_cnn_x,
        build_live_gnn_x,
        build_live_lstm_x,
        build_live_transformer_x,
    )

    if name == "lstm":
        return build_live_lstm_x(track, current)
    if name == "cnn":
        return build_live_cnn_x(track, current, cache_dir)
    if name == "transformer":
        return build_live_transformer_x(track, current, cache_dir)
    if name == "gnn":
        return build_live_gnn_x(track, current, cache_dir)
    raise InferenceCycleError(f"no real live feature builder for {name!r}")


#: How many leading (always size-1) axes to index away from each model's
#: real x_mean/x_std (as actually stored by its own
#: train_*_stage(_streaming), all fit with keepdims=True against a
#: *batched* array -- see each model's own _standardize_x) to broadcast
#: correctly against one *unbatched* live item. LSTM's own
#: _standardize_x uses no keepdims at all (mean shape (F,) already
#: broadcasts against unbatched (SEQ, F) with no squeeze), so it has no
#: entry here.
_STAT_LEADING_AXES: dict[str, int] = {
    "cnn": 1,  # (1, C, 1, 1) -> (C, 1, 1), matches an unbatched (C, H, W) item
    "transformer": 1,  # same (1, C, 1, 1) convention as CNN
    "gnn": 2,  # (1, 1, F) -> (F,), matches an unbatched (n_nodes, F) item
}


def _item_stat(name: str, value: np.ndarray) -> np.ndarray:
    for _ in range(_STAT_LEADING_AXES.get(name, 0)):
        value = value[0]
    return value


def _run_group1_model(name: str, model, raw, stats: dict, current: Fix) -> np.ndarray | None:
    """One real model's (n_leads, 3) absolute (lat, lon, wind) prediction,
    or ``None`` if it doesn't have the real standardisation stats a
    correct prediction needs (a version registered before #78)."""
    import torch

    from .real_run import displacement_to_latlon

    if "x_mean" not in stats or "y_mean" not in stats:
        return None

    item_x_mean = _item_stat(name, stats["x_mean"])
    item_x_std = _item_stat(name, stats["x_std"])

    if name == "gnn":
        node_features, topo = raw
        x_std = (node_features - item_x_mean) / item_x_std
        x_t = torch.as_tensor(x_std, dtype=torch.float32)
        edge_index = torch.as_tensor(topo.edge_index, dtype=torch.long)
        edge_attr = torch.as_tensor(topo.edge_attr, dtype=torch.float32)
        with torch.no_grad():
            pred_z = model(x_t, edge_index, edge_attr, center_index=[topo.center_index])
        pred_z = pred_z[0].cpu().numpy()
    else:
        x_std = (raw - item_x_mean) / item_x_std
        x_t = torch.as_tensor(x_std[None], dtype=torch.float32)
        with torch.no_grad():
            out = model(x_t)
        if name == "transformer":
            out = out[0]  # (track, regime) -- only the track head is real here
        pred_z = out[0].cpu().numpy()

    pred_disp = pred_z * stats["y_std"] + stats["y_mean"]
    abs_pred = np.zeros_like(pred_disp)
    for li in range(pred_disp.shape[0]):
        lat, lon = displacement_to_latlon(current.lat, current.lon, *pred_disp[li, :2])
        abs_pred[li] = [lat, lon, pred_disp[li, 2]]
    return abs_pred


def build_real_deterministic_fn(
    track: Track,
    registry: ModelRegistry,
    checkpoint_store: CheckpointStore,
    cache_dir: Path | str,
) -> Callable[[CyclePlan, Fix], DeterministicForecast]:
    """A real `deterministic_fn` closure over ``track`` (the storm's real
    known history) -- `inference.cycle.run_cycle`'s own
    ``deterministic_fn(plan, initial_fix)`` signature has no room for a
    real `Track`, only the current `Fix`, so the storm being forecast is
    captured here instead of threaded through `run_cycle` itself.

    Raises `InferenceCycleError` if no real model could contribute at
    all (no registered version in staging/production, no cached field,
    too little real history) -- the caller is responsible for a
    degraded-mode fallback (e.g. the existing synthetic/climatological
    path), the same as any other real `deterministic_fn` failure
    `run_cycle` already handles for `ensemble_fn`.
    """

    def deterministic_fn(plan: CyclePlan, current: Fix):
        from ..inference.cycle import DeterministicForecast, fusion_weights
        from ..models.base import DEFAULT_LEADS
        from ..tracking.registry import Stage
        from .real_inference import (
            InferenceLoadError,
            load_standardization_stats,
            load_trained_model,
        )

        per_model_abs: dict[str, np.ndarray] = {}
        recent_errors: dict[str, float] = {}

        for name in _GROUP1_LIVE_MODELS:
            version = registry.production(name) or registry.in_stage(name, Stage.STAGING)
            if version is None:
                continue
            raw = _build_live_x(name, track, current, cache_dir)
            if raw is None:
                continue
            try:
                model, _spec = load_trained_model(name, version, checkpoint_store)
            except InferenceLoadError:
                continue
            stats = load_standardization_stats(version)
            abs_pred = _run_group1_model(name, model, raw, stats, current)
            if abs_pred is None:
                continue

            per_model_abs[name] = abs_pred
            error = version.metrics.get("track_error_48h_nm")
            recent_errors[name] = error if error and error > 0 else _UNKNOWN_ERROR_SENTINEL

        if not per_model_abs:
            raise InferenceCycleError(
                "no real Group 1 model could contribute to this cycle -- no registered "
                "staging/production version, no real live feature, or no checkpoint to load"
            )

        weights = fusion_weights(recent_errors)
        n_leads = len(DEFAULT_LEADS)
        lats = np.zeros(n_leads)
        lons = np.zeros(n_leads)
        winds = np.zeros(n_leads)
        for name, abs_pred in per_model_abs.items():
            w = weights[name]
            lats += w * abs_pred[:, 0]
            lons += w * abs_pred[:, 1]
            winds += w * abs_pred[:, 2]

        return DeterministicForecast(
            target_time=plan.target_time, lead_hours=DEFAULT_LEADS,
            lats=lats, lons=lons, winds_kt=winds,
            contributors={name: weights[name] for name in per_model_abs},
        )

    return deterministic_fn
