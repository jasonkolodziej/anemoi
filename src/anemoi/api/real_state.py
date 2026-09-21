"""Real ingestion-backed state for Anemoi-API (#78/#85's real remainder).

Real storms from a real HURDAT2 archive (`data.hurdat2.parse_hurdat2_file`)
-- the most recent ``n_recent`` storms by season, since HURDAT2 is a
historical archive, not a live feed. A genuinely live "current storm
right now" source (real-time ATCF/TC-Vitals ingestion) is #85's own
still-open remainder, not solved here -- this closes "can the API run a
real cycle against real trained models for a real storm," using the
most recent real storms this system's real data source actually has.

Real cycles run `training.real_inference_cycle.build_real_deterministic_fn`
/`training.real_inference_ensemble.build_real_ensemble_fn` (#78/#85)
against a real `ModelRegistry`/`CheckpointStore`, with the same synthetic
linear-extrapolation fallback `demo_state.DemoState` uses whenever the
real deterministic path can't contribute for a specific cycle
(`InferenceCycleError` -- unlike `ensemble_fn`, `run_cycle` doesn't catch
a `deterministic_fn` failure itself, so this module catches it instead,
the same "never fail a cycle over a missing/incomplete real model"
contract `run_cycle`'s own ensemble degradation already establishes).

Implements the exact same public surface `DemoState` does
(`list_storms`/`get_storm`/`run_cycle`/`get_cycle`/`registry`) --
`api.routers.storms`'s own docstring already promises "swap DemoState
for a real ingestion-backed store and every route below is unchanged."
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np

from ..data.availability import LatencyOracle
from ..data.besttrack import Fix, Track, TrackQuality
from ..inference.cycle import CycleOutput, DeterministicForecast, run_cycle
from ..inference.scheduler import plan_cycle
from ..tracking.registry import ModelRegistry

#: How recently a storm's latest real fix must be to count as "active" --
#: a real, if arbitrary, threshold; a genuinely live feed would make this
#: exact rather than a heuristic over historical archive data.
_ACTIVE_WINDOW = timedelta(days=14)

#: Real forecast lead times every real deterministic_fn/ensemble_fn this
#: module builds shares -- matches models.base.DEFAULT_LEADS.
_LEAD_HOURS = (12, 24, 36, 48, 72, 96, 120)


@dataclass
class RealStormState:
    storm_id: str
    track: Track  # real FINAL-quality archive history; display + model input base
    cycles: dict[str, CycleOutput] = field(default_factory=dict)

    @property
    def season(self) -> int:
        return self.track.season

    @property
    def latest_fix(self) -> Fix:
        return self.track.fixes[-1]

    @property
    def active(self) -> bool:
        return (datetime.now(UTC) - self.latest_fix.valid_time) < _ACTIVE_WINDOW


def _synthetic_fallback_deterministic(plan, fix) -> DeterministicForecast:
    """The same linear-extrapolation fallback `demo_state.DemoState` uses
    -- not a stopgap invented for this module, the pre-existing "no real
    model available" answer, reused rather than duplicated."""
    steps = np.arange(1, len(_LEAD_HOURS) + 1, dtype=float)
    return DeterministicForecast(
        target_time=plan.target_time, lead_hours=_LEAD_HOURS,
        lats=fix.lat + 0.9 * steps, lons=fix.lon - 1.1 * steps,
        winds_kt=np.clip(fix.max_wind_kt + 4.0 * steps - 0.4 * steps**2, 15.0, None),
        contributors={},
    )


class RealState:
    """One process-lifetime instance of the real, non-demo API state.

    Opt-in (`deps.state_dependency` selects this over `DemoState` only
    when ``ANEMOI_API_REAL_STATE`` is set) -- `DemoState` stays the
    default, unchanged, always-available path.
    """

    def __init__(
        self,
        *,
        hurdat2_path: str | Path | None = None,
        registry_root: str | Path | None = None,
        checkpoint_store=None,
        cache_dir: str | Path | None = None,
        n_recent: int = 5,
    ) -> None:
        from ..data.hurdat2 import parse_hurdat2_file

        hurdat2_path = hurdat2_path or os.environ.get("HURDAT2_PATH")
        if not hurdat2_path:
            raise RuntimeError(
                "RealState needs a real HURDAT2 archive -- set HURDAT2_PATH "
                "or pass hurdat2_path explicitly"
            )
        tracks = parse_hurdat2_file(hurdat2_path)
        recent = sorted(tracks, key=lambda t: t.season)[-n_recent:]
        self.storms: dict[str, RealStormState] = {
            t.storm_id: RealStormState(t.storm_id, t) for t in recent
        }

        registry_root = registry_root or os.environ.get(
            "REGISTRY_ROOT", str(Path.home() / ".anemoi" / "registry"),
        )
        self.registry = ModelRegistry(registry_root)
        #: Built lazily (`_checkpoint_store` property) -- listing/reading
        #: real storms needs no S3 credentials at all, only running a real
        #: cycle does, and real deployments shouldn't have to configure
        #: R2/S3 just to serve GET /storms.
        self._checkpoint_store_override = checkpoint_store
        self._checkpoint_store_cache = None
        self._cache_dir = cache_dir or os.environ.get(
            "GDAS_CACHE_DIR", str(Path.home() / "gdas_cache"),
        )
        self._lock = threading.Lock()
        #: Why the most recent real deterministic_fn attempt degraded to
        #: the synthetic fallback, if it did -- InferenceCycleError's own
        #: message already carries a real per-model breakdown (#100), this
        #: just keeps the latest one around to inspect without needing
        #: container log access, which has repeatedly proven hard to get to
        #: on this deployment. Cheap to always capture (a short string);
        #: /debug/last-deterministic-error (main.py) only *exposes* it, and
        #: only when ANEMOI_API_DEBUG is set.
        self.last_deterministic_error: str | None = None

    @property
    def _checkpoint_store(self):
        if self._checkpoint_store_override is not None:
            return self._checkpoint_store_override
        if self._checkpoint_store_cache is None:
            from ..tracking.checkpoint_store import CheckpointStore, S3Config

            self._checkpoint_store_cache = CheckpointStore(S3Config.from_env())
        return self._checkpoint_store_cache

    # ---- storms ------------------------------------------------------

    def list_storms(self) -> list[RealStormState]:
        return list(self.storms.values())

    def get_storm(self, storm_id: str) -> RealStormState:
        try:
            return self.storms[storm_id]
        except KeyError as exc:
            raise LookupError(f"unknown storm {storm_id!r}") from exc

    # ---- cycles --------------------------------------------------------

    def run_cycle(
        self,
        storm_id: str,
        cycle: str,
        *,
        lat: float | None,
        lon: float | None,
        wind_kt: float | None,
        members: int,
        worst_case: bool,
        coastline: tuple[float, float] | None,
    ) -> CycleOutput:
        from ..time_utils import parse_cycle_label
        from ..training.real_inference_cycle import build_real_deterministic_fn
        from ..training.real_inference_ensemble import build_real_ensemble_fn

        storm = self.get_storm(storm_id)
        target = parse_cycle_label(cycle)
        oracle = LatencyOracle(use_max_latency=worst_case)
        plan = plan_cycle(target, oracle)

        base = storm.latest_fix
        fix = Fix(
            storm_id=storm_id,
            valid_time=target,
            lat=lat if lat is not None else base.lat,
            lon=lon if lon is not None else base.lon,
            max_wind_kt=wind_kt if wind_kt is not None else base.max_wind_kt,
            min_pressure_mb=base.min_pressure_mb,
            # A FINAL-quality archive fix is never a model input (§4.6.2) --
            # mint a fresh WORKING/ESTIMATED fix at the same position.
            quality=TrackQuality.ESTIMATED if plan.vitals_estimated else TrackQuality.WORKING,
        )

        def deterministic(plan_, fix_):
            try:
                real_deterministic = build_real_deterministic_fn(
                    storm.track, self.registry, self._checkpoint_store, self._cache_dir,
                )
                return real_deterministic(plan_, fix_)
            except Exception as exc:  # noqa: BLE001 - no real model contributing must degrade
                # Covers InferenceCycleError (no registered version, no real
                # live feature, no checkpoint) and a missing/misconfigured
                # real checkpoint store (CheckpointStoreError) alike -- both
                # mean "no real model available for this cycle," and both
                # degrade to the same synthetic fallback DemoState uses.
                self.last_deterministic_error = f"{type(exc).__name__}: {exc}"
                return _synthetic_fallback_deterministic(plan_, fix_)

        def ensemble(det, n):
            # build_real_ensemble_fn's own InferenceEnsembleError (and a
            # missing/misconfigured checkpoint store) are already caught by
            # run_cycle itself (falls back to climatological_ensemble,
            # SS10.1) -- no extra wrapping needed here, unlike deterministic
            # above, which run_cycle does NOT guard on its own.
            real_ensemble = build_real_ensemble_fn(
                storm.track, self.registry, self._checkpoint_store, self._cache_dir,
            )
            return real_ensemble(det, n)

        output = run_cycle(
            plan, fix, deterministic, lambda det, n: ensemble(det, min(members, n)),
            coastline=coastline,
        )
        with self._lock:
            storm.cycles[output.label] = output
        return output

    def get_cycle(self, storm_id: str, cycle: str) -> CycleOutput:
        storm = self.get_storm(storm_id)
        try:
            return storm.cycles[cycle]
        except KeyError as exc:
            raise LookupError(f"cycle {cycle!r} has not been run for {storm_id!r}") from exc


_REAL_STATE: RealState | None = None
_REAL_STATE_LOCK = threading.Lock()


def get_real_state() -> RealState:
    global _REAL_STATE
    if _REAL_STATE is None:
        with _REAL_STATE_LOCK:
            if _REAL_STATE is None:
                _REAL_STATE = RealState()
    return _REAL_STATE
