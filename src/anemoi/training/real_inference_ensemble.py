"""Real `ensemble_fn` for `inference.cycle.run_cycle` (#78, #85).

Built from all five Group 1 models' real `.encode()` latents -- the
same real standardized inputs `real_latents.extract_joint_latents`
already uses for training, for one live window instead of a batch --
concatenated in `real_latents.GROUP1_ORDER` (the order the real
diffusion model's own `latent_dim` was trained against), then the real,
trained `TrajectoryDenoiser.sample()`.

Unlike `real_inference_cycle`'s `deterministic_fn`, this needs all five
real Group 1 predictions with no non-learned fallback: there is no
"approximate ensemble" the way `fusion_weights` approximates
`ConsensusFusion` -- an ensemble IS the diffusion model's real product.
When it can't run, `run_cycle` already degrades to
`climatological_ensemble` on any `ensemble_fn` exception (§10.1), so
this raises rather than fabricating spread.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from ..data.besttrack import Fix, Track
    from ..inference.cycle import DeterministicForecast
    from ..inference.postprocess import EnsembleMember
    from ..tracking.checkpoint_store import CheckpointStore
    from ..tracking.registry import ModelRegistry


class InferenceEnsembleError(RuntimeError):
    pass


def _encode_group1(name: str, model, raw, stats: dict) -> np.ndarray | None:
    """One real Group 1 model's real latent vector (``.encode()``) for
    the current live window -- the same real standardized inputs
    `real_inference_cycle`'s forward-pass path builds, just stopped one
    layer earlier."""
    import torch

    from .real_inference_cycle import _item_stat

    if name == "pinn":
        env, candidate_abs = raw
        if "env_mean" not in stats:
            return None
        env_z = (env - stats["env_mean"]) / stats["env_std"]
        with torch.no_grad():
            env_t = torch.as_tensor(env_z[None], dtype=torch.float32)
            cand_t = torch.as_tensor(candidate_abs[None], dtype=torch.float32)
            latent = model.encode(env_t, cand_t)
        return latent[0].cpu().numpy()

    if "x_mean" not in stats:
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
            latent = model.encode(x_t, edge_index, edge_attr, center_index=[topo.center_index])
        return latent[0].cpu().numpy()

    x_std = (raw - item_x_mean) / item_x_std
    x_t = torch.as_tensor(x_std[None], dtype=torch.float32)
    with torch.no_grad():
        latent = model.encode(x_t)
    return latent[0].cpu().numpy()


def _build_joint_latent(
    registry: ModelRegistry, checkpoint_store: CheckpointStore,
    track: Track, current: Fix, cache_dir: Path | str,
) -> np.ndarray | None:
    """The real concatenated latent vector all five Group 1 models
    encode the current live window into, in `real_latents.GROUP1_ORDER`
    -- ``None`` if any one of the five can't contribute (no registered
    version, no real live feature, no checkpoint), since the real
    diffusion model needs the exact ``latent_dim`` it was trained
    against, not a partial vector."""
    from ..tracking.registry import Stage
    from .real_inference import (
        InferenceLoadError,
        load_standardization_stats,
        load_trained_model,
        load_trained_pinn_candidate,
    )
    from .real_inference_cycle import _build_live_x
    from .real_inference_live import build_live_pinn_x
    from .real_latents import GROUP1_ORDER

    latents: list[np.ndarray] = []
    for name in GROUP1_ORDER:
        version = registry.production(name) or registry.in_stage(name, Stage.STAGING)
        if version is None:
            return None
        try:
            model, _spec = load_trained_model(name, version, checkpoint_store)
        except InferenceLoadError:
            return None

        if name == "pinn":
            try:
                candidate_model, _cspec = load_trained_pinn_candidate(version, checkpoint_store)
            except InferenceLoadError:
                return None
            raw = build_live_pinn_x(track, current, candidate_model, cache_dir)
        else:
            raw = _build_live_x(name, track, current, cache_dir)
        if raw is None:
            return None

        stats = load_standardization_stats(version)
        latent = _encode_group1(name, model, raw, stats)
        if latent is None:
            return None
        latents.append(latent)

    return np.concatenate(latents)


def build_real_ensemble_fn(
    track: Track,
    registry: ModelRegistry,
    checkpoint_store: CheckpointStore,
    cache_dir: Path | str,
) -> Callable[[DeterministicForecast, int], list[EnsembleMember]]:
    """A real `ensemble_fn` closure over ``track``, for
    `inference.cycle.run_cycle` -- the same reason
    `real_inference_cycle.build_real_deterministic_fn` needed a closure.
    ``ensemble_fn(deterministic, n_members)`` has no room for a real
    `Track` either, and not even the current `Fix` -- only
    ``deterministic.target_time``, which `run_cycle`'s own guardrail
    already asserts equals ``initial_fix.valid_time``, so ``track
    .window_ending(deterministic.target_time, 1)`` recovers the real
    current fix from it.

    Raises `InferenceEnsembleError` if the real diffusion model can't
    run for this cycle (fewer than five real Group 1 predictions, no
    registered diffusion version, or no real standardisation stats) --
    `run_cycle` already catches any `ensemble_fn` exception and degrades
    to `climatological_ensemble` (§10.1), so this raises freely rather
    than fabricating spread.
    """

    def ensemble_fn(deterministic: DeterministicForecast, n_members: int) -> list[EnsembleMember]:
        import torch

        from ..inference.postprocess import EnsembleMember
        from ..tracking.registry import Stage
        from .real_inference import (
            InferenceLoadError,
            load_standardization_stats,
            load_trained_model,
        )
        from .real_run import displacement_to_latlon

        window = track.window_ending(deterministic.target_time, 1)
        if window is None:
            raise InferenceEnsembleError(
                f"no real fix in track at {deterministic.target_time} -- can't build live latents"
            )
        current = window[0]

        z = _build_joint_latent(registry, checkpoint_store, track, current, cache_dir)
        if z is None:
            raise InferenceEnsembleError(
                "not all five real Group 1 models could contribute a live latent "
                "for this cycle -- the real diffusion ensemble needs all five"
            )

        version = registry.production("diffusion") or registry.in_stage("diffusion", Stage.STAGING)
        if version is None:
            raise InferenceEnsembleError("no registered diffusion version in staging/production")
        try:
            model, spec = load_trained_model("diffusion", version, checkpoint_store)
        except InferenceLoadError as exc:
            raise InferenceEnsembleError(
                f"could not load the real diffusion checkpoint: {exc}"
            ) from exc

        stats = load_standardization_stats(version)
        if "z_mean" not in stats or "y_mean" not in stats:
            raise InferenceEnsembleError(
                f"diffusion v{version.version} has no real standardisation stats to load"
            )

        z_z = (z - stats["z_mean"]) / stats["z_std"]
        with torch.no_grad():
            z_t = torch.as_tensor(z_z[None], dtype=torch.float32)
            samples_z = model.sample(z_t, n_members=n_members).cpu().numpy()

        samples_disp = samples_z * stats["y_std"] + stats["y_mean"]
        lead_hours = spec.lead_hours
        n_leads = samples_disp.shape[1]

        members: list[EnsembleMember] = []
        for mi in range(samples_disp.shape[0]):
            lats = np.zeros(n_leads)
            lons = np.zeros(n_leads)
            winds = np.zeros(n_leads)
            for li in range(n_leads):
                lat, lon = displacement_to_latlon(
                    current.lat, current.lon, *samples_disp[mi, li, :2],
                )
                lats[li] = lat
                lons[li] = lon
                winds[li] = samples_disp[mi, li, 2]
            members.append(
                EnsembleMember(
                    member_id=mi, lead_hours=lead_hours, lats=lats, lons=lons, winds_kt=winds,
                )
            )
        return members

    return ensemble_fn
