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

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from ..data.besttrack import Fix, Track
    from ..data.features import GriddedFields
    from ..time_utils import NWPCycleSelection
    from .real_run_gnn import MeshTopology

#: A `(track, current, cache_dir) -> GriddedFields | None` field source --
#: every `build_live_*_x` builder below takes one as an optional override
#: (default `_current_fields`, the real live/operational GDAS path).
#: `monitoring.skew_audit` is the one real caller that passes a different
#: one (`era5t_fields`, below): the skew audit's entire point (§4.6.3) is
#: re-running the exact same live-inference path on an ERA5T-sourced field
#: instead of a GDAS one, not a separate parallel implementation of it.
FieldsFetcher = Callable[["Track", "Fix", "Path | str"], "GriddedFields | None"]


def gdas_likely_unpublished(
    valid_time: datetime, now: datetime | None = None, *, lead_hours: int | None = None,
) -> bool:
    """True if the GFS file a live cycle at ``valid_time`` reads is still
    inside its typical publish latency (``data.sources.get("gdas_gfs")``,
    ~3.5h) as of ``now``. Since #215 that file is the ``t-6`` cycle's
    ``f006`` (``lead_hours`` defaults to ``NWP_LAG_HOURS``), published
    around t-2:30 -- so for a cycle run at t+1:30 this is normally False.

    Purely diagnostic -- used only to give a `missing_model_reasons` entry
    a more specific, honest explanation when the fetch comes back empty.
    Deliberately NOT used to skip the fetch attempt itself: real GDAS
    publication timing has genuine variance around its typical latency.
    """
    from datetime import timedelta

    from ..data import sources
    from ..time_utils import NWP_LAG_HOURS

    if now is None:
        now = datetime.now(UTC)
    lead = NWP_LAG_HOURS if lead_hours is None else lead_hours
    latency = sources.get("gdas_gfs").typical_latency
    return valid_time - timedelta(hours=lead) + latency > now


def _current_window(track: Track, current: Fix, length: int) -> tuple[Fix, ...] | None:
    return track.window_ending(current.valid_time, length)


def live_cache_path(cache_dir: Path | str, storm_id: str, current: Fix, lead_hours: int) -> Path:
    """Where a live cycle's fetched fields are kept: by storm, time, forecast
    hour *and* position (#215). Keyed by storm and time alone, a cycle run
    with a position override -- or after NHC corrected the fix -- reused the
    patch centred on the first position it saw."""
    name = (
        f"{current.valid_time:%Y%m%d%H}_f{lead_hours:03d}"
        f"_{current.lat:+.2f}_{current.lon:+.2f}.npz"
    )
    return Path(cache_dir) / "live" / storm_id / name


def fetch_live_nwp(
    track: Track, current: Fix, cache_dir: Path | str,
) -> tuple[GriddedFields | None, NWPCycleSelection | None]:
    """The gridded fields a live cycle at ``current.valid_time`` runs on,
    and which NWP cycle they came from (#215).

    The forecast valid at the cycle time from the ``t-6`` GFS cycle
    (``f006``) -- §6.2.1's rule, which until #215 was planned and reported
    but never applied: the live path fetched the ``t`` *analysis*, which
    isn't published until ~t+3:30, two hours after the cycle runs, so the
    gridded models almost never contributed to a scheduled cycle. If the
    ``t-6`` cycle isn't there, the ``t-12`` cycle's ``f012`` (degraded,
    ``nwp_stale=12h``); if neither, ``(None, None)`` -- §4.6.4's LSTM +
    climatology mode.

    Fetched fields are cached under ``cache_dir/live`` (`live_cache_path`).
    Before `GDAS_ARCHIVE_START` there is nothing to fetch.
    """
    from datetime import timedelta

    from ..data.gdas_cache import GDAS_ARCHIVE_START, fetch_one
    from ..data.gridded_cache import FetchTask, load_cached_fields, save_cached_fields
    from ..time_utils import MAX_NWP_LAG_HOURS, NWP_LAG_HOURS, NWPCycleSelection

    if current.valid_time < GDAS_ARCHIVE_START:
        return None, None
    for lag in range(NWP_LAG_HOURS, MAX_NWP_LAG_HOURS + 1, NWP_LAG_HOURS):
        path = live_cache_path(cache_dir, track.storm_id, current, lag)
        fields = None
        if path.exists():
            try:
                fields = load_cached_fields(path)
            except Exception:  # noqa: BLE001 - a corrupt cache entry is re-fetched
                fields = None
        if fields is None:
            try:
                fields = fetch_one(current.valid_time, current.lat, current.lon, lead_hours=lag)
            except Exception:  # noqa: BLE001 - this cycle not published (yet); try the older one
                continue
            save_cached_fields(
                path, fields,
                FetchTask(track.storm_id, current.valid_time, current.lat, current.lon),
            )
        return fields, NWPCycleSelection(
            target_time=current.valid_time,
            nwp_cycle=current.valid_time - timedelta(hours=lag),
            lag_hours=lag, forecast_hour=lag, degraded=lag > NWP_LAG_HOURS,
        )
    return None, None


def _current_fields(track: Track, current: Fix, cache_dir: Path | str) -> GriddedFields | None:
    """The live cycle's `GriddedFields` (`fetch_live_nwp`), or ``None`` when
    no NWP cycle within the staleness budget has them -- the `FieldsFetcher`
    every `build_live_*_x` builder defaults to. Any failure degrades to
    ``None``, the same "this model can't contribute to this cycle" contract
    every caller here already handles."""
    return fetch_live_nwp(track, current, cache_dir)[0]


def era5t_fields(track: Track, current: Fix, cache_dir: Path | str) -> GriddedFields | None:
    """The current fix's `GriddedFields`, sourced from ERA5T instead of
    GDAS -- same `FieldsFetcher` signature as `_current_fields` (``cache_dir``
    is accepted but unused; the skew audit runs infrequently enough offline
    that per-sample Zarr reads need no on-disk cache the way the hot live
    GDAS path does) so it's a drop-in override for any `build_live_*_x`
    builder. `None` under the same "this model can't contribute" contract
    every other fetch here already has: too old for ERA5T's own real
    availability window is the caller's job to check (`monitoring.skew
    .audit_due`) before ever calling this, not this function's; a `None`
    here means the real Zarr read itself failed (network, or ERA5T's
    ``valid_time_stop_era5t`` hasn't actually reached this hour yet despite
    `audit_due` saying it should have -- real-world latency has variance
    around the typical figure, same reasoning as `gdas_likely_unpublished`'s
    own docstring)."""
    from dataclasses import replace

    from ..data.real_gridded import fetch_era5t_one

    del cache_dir
    try:
        fields = fetch_era5t_one(current.valid_time, current.lat, current.lon)
    except Exception:  # noqa: BLE001 - no real field available must degrade, never crash
        return None
    return replace(fields, source="era5t")


era5t_fields.source_name = "era5t"  # type: ignore[attr-defined] - read by the cycle's provenance


def build_live_lstm_x(track: Track, current: Fix) -> np.ndarray | None:
    """LSTM's real input: the storm-relative sequence over its most
    recent real fixes, no gridded fields needed at all."""
    from ..data.storm_relative import storm_relative_sequence
    from .capacity_ablation import SEQUENCE_LENGTH

    window = _current_window(track, current, SEQUENCE_LENGTH + 1)
    if window is None:
        return None
    return storm_relative_sequence(window)


def build_live_cnn_x(
    track: Track, current: Fix, cache_dir: Path | str,
    *, fields_fetcher: FieldsFetcher | None = None,
) -> np.ndarray | None:
    from .real_run_cnn import _sanitized_channel_stack

    fields = (fields_fetcher or _current_fields)(track, current, cache_dir)
    if fields is None:
        return None
    return _sanitized_channel_stack(fields)


def build_live_transformer_x(
    track: Track, current: Fix, cache_dir: Path | str,
    *, fields_fetcher: FieldsFetcher | None = None,
) -> np.ndarray | None:
    from .real_run_transformer import GRID_SIZE, _sanitized_channel_stack

    fields = (fields_fetcher or _current_fields)(track, current, cache_dir)
    if fields is None:
        return None
    stack = _sanitized_channel_stack(fields)
    if stack is None:
        return None
    gh, gw = GRID_SIZE
    return stack[:, :gh, :gw]


def build_live_pinn_x(
    track: Track, current: Fix, candidate_model, cache_dir: Path | str,
    *, fields_fetcher: FieldsFetcher | None = None,
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

    fields = (fields_fetcher or _current_fields)(track, current, cache_dir)
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
    *, fields_fetcher: FieldsFetcher | None = None,
) -> tuple[np.ndarray, MeshTopology] | None:
    """GNN needs its mesh topology alongside the node features (`models
    .gnn.build_gnn`'s ``forward`` takes ``edge_index``/``edge_attr``
    directly, not baked into the model) -- built fresh from the cached
    field's own shape, the same cheap "pure function of shape/stride"
    real_run_gnn's own module docstring already establishes for the
    training path.
    """
    from .real_run_gnn import GNN_STRIDE, _node_features, build_mesh_topology

    fields = (fields_fetcher or _current_fields)(track, current, cache_dir)
    if fields is None:
        return None
    topo = build_mesh_topology(fields.shape, stride or GNN_STRIDE)
    node_features = _node_features(fields, topo)
    if node_features is None:
        return None
    return node_features, topo
