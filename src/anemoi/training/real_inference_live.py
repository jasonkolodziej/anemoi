"""Real-time feature building for live inference (#78).

Every existing ``build_<model>_samples``/streaming ``build_x`` function is
training-oriented: it's built on `real_run.iter_stage_windows`, which
discards a window whose future target can't be computed at all
(``if not mask.any(): continue``) -- exactly the situation a live
inference cycle is always in, since there's no future fix yet by
definition. The functions here build the same real ``x`` representation
training used (raw, unstandardized -- the caller applies
`real_inference.load_standardization_stats`' real mean/std), for the
current moment, with no target needed or computed at all.

Each takes a real `data.besttrack.Track` (the storm's real known history)
and its most recent real `Fix` (``current`` -- the same pair
`inference.cycle.run_cycle`'s ``deterministic_fn(plan, initial_fix)``
already receives), and returns ``None`` -- not an exception -- exactly
when the equivalent training-time builder would have skipped the window:
not enough real history yet, or no cached/live gridded field for the
current position/time. A real caller (a live inference runner) must
treat ``None`` as "this model can't contribute to this cycle," the same
"skip, don't crash" contract used everywhere else in this codebase.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from ..data.besttrack import Fix, Track
    from ..data.features import GriddedFields
    from .real_run_gnn import MeshTopology


def _current_window(track: Track, current: Fix, length: int) -> tuple[Fix, ...] | None:
    return track.window_ending(current.valid_time, length)


def _current_fields(track: Track, current: Fix, cache_dir: Path | str) -> GriddedFields | None:
    """The current fix's `GriddedFields` -- the same real cache lookup
    CNN/Transformer/GNN/PINN's training builders already use, falling back
    to a real, on-demand GDAS fetch (#98) on a cache miss instead of giving
    up. GDAS, not ERA5: live/operational inference is always the
    operational flavor (every real registered version already requires
    `Flavor.GDAS_FINETUNE`, see `tracking.registry.ModelRegistry.register`),
    and GDAS's real archive covers any storm from 2021 onward
    (`data.gdas_cache.GDAS_ARCHIVE_START`) -- including any real HURDAT2
    storm `RealState` can serve today, not just a genuinely live one.

    Fetched fields are saved to `cache_dir` (same real on-disk format
    `run_fetch_cache` writes), so a repeat cycle for the same storm/time
    doesn't re-fetch. Any failure here (network, an eccodes/libeccodes
    install gap -- see `real_gridded.require_gdas_deps`'s docstring --
    before GDAS_ARCHIVE_START, or GDAS simply not having this exact
    synoptic hour) degrades to `None`, the same "this model can't
    contribute to this cycle" contract every caller here already has to
    handle regardless of the reason.
    """
    from ..data.gridded_cache import FetchTask, cache_path, load_cached_fields, save_cached_fields

    task = FetchTask(
        storm_id=track.storm_id, valid_time=current.valid_time, lat=current.lat, lon=current.lon,
    )
    path = cache_path(cache_dir, task)
    if path.exists():
        return load_cached_fields(path)

    from ..data.gdas_cache import GDAS_ARCHIVE_START

    if current.valid_time < GDAS_ARCHIVE_START:
        return None

    try:
        from ..data.gdas_cache import fetch_one

        fields = fetch_one(current.valid_time, current.lat, current.lon)
    except Exception:  # noqa: BLE001 - no real field available must degrade, never crash a cycle
        return None
    save_cached_fields(path, fields, task)
    return fields


def build_live_lstm_x(track: Track, current: Fix) -> np.ndarray | None:
    """LSTM's real input: the storm-relative sequence over its most
    recent real fixes, no gridded fields needed at all."""
    from ..data.storm_relative import storm_relative_sequence
    from .capacity_ablation import SEQUENCE_LENGTH

    window = _current_window(track, current, SEQUENCE_LENGTH + 1)
    if window is None:
        return None
    return storm_relative_sequence(window)


def build_live_cnn_x(track: Track, current: Fix, cache_dir: Path | str) -> np.ndarray | None:
    from .real_run_cnn import _sanitized_channel_stack

    fields = _current_fields(track, current, cache_dir)
    if fields is None:
        return None
    return _sanitized_channel_stack(fields)


def build_live_transformer_x(
    track: Track, current: Fix, cache_dir: Path | str,
) -> np.ndarray | None:
    from .real_run_transformer import GRID_SIZE, _sanitized_channel_stack

    fields = _current_fields(track, current, cache_dir)
    if fields is None:
        return None
    stack = _sanitized_channel_stack(fields)
    if stack is None:
        return None
    gh, gw = GRID_SIZE
    return stack[:, :gh, :gw]


def build_live_pinn_x(
    track: Track, current: Fix, candidate_model, cache_dir: Path | str,
) -> tuple[np.ndarray, np.ndarray] | None:
    """PINN's real input: the environment-feature vector plus its
    candidate-generator LSTM's own forecast, converted to absolute (lat,
    lon, wind) -- `models.pinn.PhysicsCorrector.forward(environment,
    candidate)` takes the candidate already in that space (module
    docstring; mirrors `real_run_pinn._candidate_and_true_absolute`'s
    training-time conversion, for one live window instead of a batch).

    Unlike the other three gridded-field models, this needs a real,
    already-loaded candidate LSTM (`real_inference.load_trained_pinn_candidate`)
    as an argument rather than loading one itself -- building this
    feature inherently requires running that model's forward pass, the
    same way training runs the candidate before the outer corrector.

    Returns ``None`` under the same conditions the training-time
    builder skips a window for: no cached field for the current
    position/time, a non-finite environment vector (a storm-centred box
    entirely over land -- real ERA5 SST has no ocean pixel there at all,
    see `data.features.area_mean`'s docstring), or too little real
    history for the candidate's own input sequence.
    """
    import torch

    from ..data.features import compute_environment_features
    from .capacity_ablation import SEQUENCE_LENGTH
    from .real_run import displacement_to_latlon

    fields = _current_fields(track, current, cache_dir)
    if fields is None:
        return None
    try:
        env = compute_environment_features(fields).values
    except ValueError:
        return None

    window = _current_window(track, current, SEQUENCE_LENGTH + 1)
    if window is None:
        return None

    from ..data.storm_relative import storm_relative_sequence

    x_track = storm_relative_sequence(window)
    with torch.no_grad():
        xt = torch.as_tensor(x_track[None], dtype=torch.float32)
        pred_disp = candidate_model(xt).cpu().numpy()[0]

    candidate_abs = np.zeros_like(pred_disp)
    for li in range(pred_disp.shape[0]):
        lat, lon = displacement_to_latlon(current.lat, current.lon, *pred_disp[li, :2])
        candidate_abs[li] = [lat, lon, pred_disp[li, 2]]

    return env, candidate_abs


def build_live_gnn_x(
    track: Track, current: Fix, cache_dir: Path | str, stride: int | None = None,
) -> tuple[np.ndarray, MeshTopology] | None:
    """GNN needs its mesh topology alongside the node features (`models
    .gnn.build_gnn`'s ``forward`` takes ``edge_index``/``edge_attr``
    directly, not baked into the model) -- built fresh from the cached
    field's own shape, the same cheap "pure function of shape/stride"
    real_run_gnn's own module docstring already establishes for the
    training path.
    """
    from .real_run_gnn import GNN_STRIDE, _node_features, build_mesh_topology

    fields = _current_fields(track, current, cache_dir)
    if fields is None:
        return None
    topo = build_mesh_topology(fields.shape, stride or GNN_STRIDE)
    node_features = _node_features(fields, topo)
    if node_features is None:
        return None
    return node_features, topo
