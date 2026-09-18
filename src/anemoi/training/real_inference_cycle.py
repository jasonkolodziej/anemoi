"""Real `deterministic_fn` for `inference.cycle.run_cycle` (#78, #85).

Built from all five Group 1 models' real trained checkpoints
(`real_inference.load_trained_model`) and real live features
(`real_inference_live.build_live_<model>_x`). When all five real
predictions are available, combines them via the real, learned
`ConsensusFusion` model (`real_inference.load_trained_model("fusion",
...)`) -- the system's actual §6.1 fusion layer, not an approximation of
it. When fewer than five are (a real registered version is missing, a
live feature couldn't be built, PINN's storm is entirely over land...),
falls back to the real, existing non-learned inverse-error consensus
(`inference.cycle.fusion_weights`, §10.1 divergence handling) using each
contributing model's own recorded validation error -- `ConsensusFusion`
has a fixed ``n_models=5`` and cannot run at all with fewer.
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

#: Group 1 models with a real live feature builder (`real_inference_live`),
#: in `real_latents.GROUP1_ORDER`'s exact order -- the order the real
#: fusion model's predictions tensor was trained against.
_GROUP1_LIVE_MODELS: tuple[str, ...] = ("lstm", "cnn", "transformer", "gnn", "pinn")


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


def _run_pinn(
    registry: ModelRegistry, checkpoint_store: CheckpointStore,
    track: Track, current: Fix, cache_dir: Path | str,
) -> np.ndarray | None:
    """PINN's own (n_leads, 3) absolute prediction -- structurally
    different from the other four: two real models to load (the
    corrector and its candidate), and its output needs no
    un-standardization at all (`PhysicsCorrector`'s own output is
    already absolute, module docstring's own note). Returns ``None`` for
    any of the same real reasons the other models' path can: no
    registered version, no real live feature, no checkpoint to load.
    """
    from ..tracking.registry import Stage
    from .real_inference import (
        InferenceLoadError,
        load_standardization_stats,
        load_trained_model,
        load_trained_pinn_candidate,
    )
    from .real_inference_live import build_live_pinn_x

    version = registry.production("pinn") or registry.in_stage("pinn", Stage.STAGING)
    if version is None:
        return None
    try:
        model, _spec = load_trained_model("pinn", version, checkpoint_store)
        candidate_model, _cspec = load_trained_pinn_candidate(version, checkpoint_store)
    except InferenceLoadError:
        return None

    raw = build_live_pinn_x(track, current, candidate_model, cache_dir)
    if raw is None:
        return None
    env, candidate_abs = raw

    stats = load_standardization_stats(version)
    if "env_mean" not in stats or "env_std" not in stats:
        return None

    import torch

    env_z = (env - stats["env_mean"]) / stats["env_std"]

    with torch.no_grad():
        env_t = torch.as_tensor(env_z[None], dtype=torch.float32)
        cand_t = torch.as_tensor(candidate_abs[None], dtype=torch.float32)
        pred = model(env_t, cand_t)
    return pred[0].cpu().numpy()


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


def _build_live_context(track: Track, current: Fix) -> np.ndarray | None:
    """The real fusion model's `context` vector (`real_latents
    .CONTEXT_FEATURE_NAMES`) for the current moment -- `real_latents
    ._context_features` only ever reads a window's own track data
    (heading, speed, intensity trend, season), never a future target, so
    it's directly reusable for live inference; only the "enough real
    history" check is new here."""
    from .capacity_ablation import SEQUENCE_LENGTH
    from .real_latents import _context_features
    from .real_run import StageWindow

    window = track.window_ending(current.valid_time, SEQUENCE_LENGTH + 1)
    if window is None:
        return None
    sw = StageWindow(
        storm_id=track.storm_id, window=window, current=current,
        y=np.zeros((1, 3)), mask=np.zeros((1,), dtype=bool),
    )
    return _context_features(sw)


def _real_fusion_forecast(
    registry: ModelRegistry, checkpoint_store: CheckpointStore,
    track: Track, current: Fix, per_model_abs: dict[str, np.ndarray],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, float]] | None:
    """The real, learned `ConsensusFusion` combination -- only possible
    when all five real Group 1 predictions are present, `fusion` itself
    has a registered version, and there's enough real history for its
    context vector. Returns ``None`` (not an exception) for the caller
    to fall back to the non-learned consensus on any of those."""
    from ..tracking.registry import Stage
    from .real_inference import InferenceLoadError, load_trained_model

    if set(per_model_abs) != set(_GROUP1_LIVE_MODELS):
        return None
    version = registry.production("fusion") or registry.in_stage("fusion", Stage.STAGING)
    if version is None:
        return None
    context = _build_live_context(track, current)
    if context is None:
        return None
    try:
        model, _spec = load_trained_model("fusion", version, checkpoint_store)
    except InferenceLoadError:
        return None

    import torch

    predictions = np.stack([per_model_abs[name] for name in _GROUP1_LIVE_MODELS])
    with torch.no_grad():
        pred_t = torch.as_tensor(predictions[None], dtype=torch.float32)
        ctx_t = torch.as_tensor(context[None], dtype=torch.float32)
        out = model(pred_t, ctx_t)[0].cpu().numpy()
        # model.weights() -> (1, n_leads, n_models); average over leads for
        # one real per-model summary weight (DeterministicForecast
        # .contributors is dict[str, float], not per-lead).
        per_lead_weights = model.weights(ctx_t)[0].cpu().numpy()
    mean_weights = per_lead_weights.mean(axis=0)
    contributors = dict(zip(_GROUP1_LIVE_MODELS, (float(w) for w in mean_weights), strict=True))
    return out[:, 0], out[:, 1], out[:, 2], contributors


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
            if name == "pinn":
                abs_pred = _run_pinn(registry, checkpoint_store, track, current, cache_dir)
                version = registry.production("pinn") or registry.in_stage("pinn", Stage.STAGING)
            else:
                version = registry.production(name) or registry.in_stage(name, Stage.STAGING)
                abs_pred = None
                if version is not None:
                    raw = _build_live_x(name, track, current, cache_dir)
                    if raw is not None:
                        try:
                            model, _spec = load_trained_model(name, version, checkpoint_store)
                            stats = load_standardization_stats(version)
                            abs_pred = _run_group1_model(name, model, raw, stats, current)
                        except InferenceLoadError:
                            abs_pred = None
            if abs_pred is None or version is None:
                continue

            per_model_abs[name] = abs_pred
            error = version.metrics.get("track_error_48h_nm")
            recent_errors[name] = error if error and error > 0 else _UNKNOWN_ERROR_SENTINEL

        if not per_model_abs:
            raise InferenceCycleError(
                "no real Group 1 model could contribute to this cycle -- no registered "
                "staging/production version, no real live feature, or no checkpoint to load"
            )

        n_leads = len(DEFAULT_LEADS)
        real_fusion = _real_fusion_forecast(
            registry, checkpoint_store, track, current, per_model_abs,
        )
        if real_fusion is not None:
            lats, lons, winds, contributors = real_fusion
        else:
            weights = fusion_weights(recent_errors)
            lats = np.zeros(n_leads)
            lons = np.zeros(n_leads)
            winds = np.zeros(n_leads)
            for name, abs_pred in per_model_abs.items():
                w = weights[name]
                lats += w * abs_pred[:, 0]
                lons += w * abs_pred[:, 1]
                winds += w * abs_pred[:, 2]
            contributors = {name: weights[name] for name in per_model_abs}

        return DeterministicForecast(
            target_time=plan.target_time, lead_hours=DEFAULT_LEADS,
            lats=lats, lons=lons, winds_kt=winds, contributors=contributors,
        )

    return deterministic_fn
