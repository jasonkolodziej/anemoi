"""Real ingestion-backed state for Anemoi-API (#78/#85's real remainder).

Real storms from a real HURDAT2 archive (`data.hurdat2.parse_hurdat2_file`)
-- the most recent ``n_recent`` storms by season, since HURDAT2 is a
historical archive, not a live feed -- merged with real, currently-active
storms from `data.live_atcf.fetch_live_tracks` (NHC's real `CurrentStorms
.json` + TC-Vitals bulletins). The live merge closes the gap this
module's docstring used to describe as still-open: "can the API run a
real cycle against real trained models for a real storm," now including a
storm actually happening right now, not just the archive.

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
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from ..training.triggers import RetrainJob

from ..data.availability import LatencyOracle
from ..data.besttrack import Fix, Track, TrackQuality
from ..inference.cycle import CycleError, CycleOutput, DeterministicForecast, run_cycle
from ..inference.scheduler import plan_cycle
from ..monitoring.drift import DriftError, DriftReport, ReferenceDistribution, detect_feature_drift
from ..monitoring.skew import SkewMonitor, SkewReport, SkewSample
from ..tracking.registry import ALL_MODELS, ModelRegistry
from . import schemas
from .cycle_store import CycleHistory

#: How recently a storm's latest real fix must be to count as "active" --
#: still used for archive storms (HURDAT2 has no live signal to be exact
#: about); a live storm's own `active` is exact by construction (it's on
#: NHC's real CurrentStorms.json right now).
_ACTIVE_WINDOW = timedelta(days=14)

#: How long a fetched live-storm snapshot stays valid before the next
#: `list_storms`/`get_storm` call re-fetches -- real TC-Vitals bulletins
#: land roughly every synoptic cycle (see `data.sources.REGISTRY`'s
#: `besttrack_working` 45/90min typical/max latency), so re-fetching more
#: often than that just re-requests the same bulletin.
_LIVE_STORMS_TTL = timedelta(minutes=30)

#: How long the registered-model registry stays valid before a real cycle
#: re-pulls it -- real promotions/registrations only ever happen once per
#: training run (hours apart) or a rare manual promotion, so this is
#: deliberately less aggressive than `_LIVE_STORMS_TTL`.
_REGISTRY_TTL = timedelta(minutes=15)

#: How long the real skew-sample corpus (#148) stays valid before a
#: process re-pulls it from durable storage -- new real samples land at
#: most as often as `anemoi skew-audit` is run (an offline, infrequent
#: batch job, not a per-cycle thing), so this is deliberately less
#: aggressive than `_REGISTRY_TTL`.
_SKEW_SAMPLES_TTL = timedelta(hours=6)

#: Real forecast lead times every real deterministic_fn/ensemble_fn this
#: module builds shares -- matches models.base.DEFAULT_LEADS.
_LEAD_HOURS = (12, 24, 36, 48, 72, 96, 120)


@dataclass
class RealStormState:
    storm_id: str
    #: FINAL-quality archive history for an archive storm, or a single
    #: WORKING-quality live track for a currently-active one (never mixed
    #: -- Track.__post_init__ forbids it; a storm gets one or the other,
    #: never both, since HURDAT2's archive and live storm-ids don't
    #: overlap in practice today).
    track: Track
    cycles: CycleHistory = field(default_factory=CycleHistory)

    @property
    def season(self) -> int:
        return self.track.season

    @property
    def name(self) -> str | None:
        return self.track.name

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
        #: Stored cycle labels by storm (#175), listed from durable storage
        #: once per process (`_ensure_cycle_index`); None until that works.
        self._cycle_index: dict[str, set[str]] | None = None
        self.storms: dict[str, RealStormState] = {
            t.storm_id: self._new_storm_state(t) for t in recent
        }
        #: Live storms, fetched lazily/re-fetched on TTL expiry rather than
        #: once here at construction -- this process/container instance
        #: can stay warm for hours (Cloudflare Containers run this as a
        #: long-lived singleton; a redeploy doesn't restart it), so a
        #: fetch-once-at-init snapshot would go stale for the rest of that
        #: lifetime. Kept separate from `self.storms` (not merged into it)
        #: so a live fetch failure can never evict an already-known live
        #: storm or disturb the archive storms.
        self._live_storms: dict[str, RealStormState] = {}
        self._live_storms_fetched_at: datetime | None = None

        registry_root = registry_root or os.environ.get(
            "REGISTRY_ROOT", str(Path.home() / ".anemoi" / "registry"),
        )
        self.registry = ModelRegistry(registry_root)
        #: Re-pulled on a TTL from run_cycle (below), not just once here --
        #: this registry was built with no checkpoint_store (construction
        #: must not need S3 credentials just to serve GET /storms), so its
        #: one-time `_load` only ever reads whatever `anemoi registry-pull`
        #: wrote to local disk at container cold-start (docker/api
        #: Dockerfile's CMD). Without a periodic reload, a long-lived warm
        #: container (same singleton-instance behaviour as the live-storms
        #: staleness above) would never see a training run's new
        #: registrations/promotions until its next cold start.
        self._registry_fetched_at: datetime | None = None

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

        #: Real drift-detection state (#148) -- a rolling in-memory window
        #: of this process's own real `env_features` (shared across models:
        #: `data.features.compute_environment_features` is model-agnostic,
        #: computed once per cycle regardless of which Group 1 models
        #: contributed). Saved to durable storage after each cycle and
        #: restored on first use (`_ensure_drift_restored`, #175) -- the
        #: container restarts on every deploy and sleeps when idle (#172),
        #: so an in-memory-only window rarely reached `detect_feature_drift`'s
        #: 30-sample minimum. Capped so it can't grow unbounded.
        self._live_env_features: list[np.ndarray] = []
        self._live_env_features_max = 500
        #: Which models have contributed to at least one real cycle this
        #: process's lifetime -- `drift_report(model)` for a model that
        #: never has is an honest n_live=0, not the shared assessment.
        self._models_ever_contributed: set[str] = set()
        #: Whether the durable drift window has been merged in yet. Until it
        #: has, nothing is written back, so a failed restore can never
        #: overwrite the stored history with just this process's samples.
        self._drift_restored = False
        #: Lazy, loaded at most once per process (not TTL-refreshed like
        #: the registry -- a reference is fit rarely, offline, by
        #: `anemoi drift-reference-fit`, not something that changes
        #: mid-process the way registrations/promotions do).
        self._drift_reference: ReferenceDistribution | None = None
        self._drift_reference_load_attempted = False

        #: Real skew-audit state (#148's remaining half). Unlike the drift
        #: reference (fit rarely, offline, loaded once per process), new
        #: real `SkewSample`s land continuously as `anemoi skew-audit` runs
        #: -- likely on a schedule, likely from a different machine -- so
        #: this is refreshed on a TTL rather than loaded once at cold
        #: start; see `_get_skew_samples`.
        self._skew_samples: list[SkewSample] | None = None
        self._skew_samples_fetched_at: datetime | None = None

    @property
    def _checkpoint_store(self):
        if self._checkpoint_store_override is not None:
            return self._checkpoint_store_override
        if self._checkpoint_store_cache is None:
            from ..tracking.checkpoint_store import CheckpointStore, S3Config

            self._checkpoint_store_cache = CheckpointStore(S3Config.from_env())
        return self._checkpoint_store_cache

    # ---- storms ------------------------------------------------------

    def _refresh_live_storms(self) -> None:
        """Re-fetch NHC's real current-storm feed if the last fetch is
        stale (or there hasn't been one yet). Best-effort: a failed fetch
        just keeps whatever live storms were already known, exactly the
        "no real X available must degrade, never crash" contract every
        other real-data fetch in this codebase follows -- see
        `data.live_atcf.fetch_live_tracks`, which itself never raises."""
        now = datetime.now(UTC)
        if (
            self._live_storms_fetched_at is not None
            and now - self._live_storms_fetched_at < _LIVE_STORMS_TTL
        ):
            return
        from ..data.live_atcf import fetch_live_tracks

        tracks = fetch_live_tracks()
        if tracks:
            # Carry each storm's cycle history over: rebuilding it empty
            # dropped every cycle run on a live storm on each refresh (#175).
            self._live_storms = {
                t.storm_id: self._new_storm_state(t, self._live_storms.get(t.storm_id))
                for t in tracks
            }
        self._live_storms_fetched_at = now

    def _new_storm_state(
        self, track: Track, previous: RealStormState | None = None,
    ) -> RealStormState:
        cycles = previous.cycles if previous is not None else CycleHistory(
            track.storm_id, self._load_stored_cycle,
        )
        if self._cycle_index is not None:
            cycles.add_stored(self._cycle_index.get(track.storm_id, ()))
        return RealStormState(track.storm_id, track, cycles)

    def _load_stored_cycle(self, storm_id: str, label: str) -> schemas.CycleResult:
        from .cycle_store import load_cycle_result

        return load_cycle_result(self._checkpoint_store, storm_id, label)

    def _ensure_cycle_index(self) -> None:
        """List stored cycle labels once per process and attach them to every
        known storm (#175). Only labels -- each result is downloaded when first
        read. Retried on the next request if storage isn't configured or
        reachable; storms still work without it, just without older cycles."""
        if self._cycle_index is not None:
            return
        from .cycle_store import list_cycle_labels

        try:
            index = list_cycle_labels(self._checkpoint_store)
        except Exception:  # noqa: BLE001 - no store configured, or unreachable right now
            return
        self._cycle_index = index
        for storm in [*self.storms.values(), *self._live_storms.values()]:
            storm.cycles.add_stored(index.get(storm.storm_id, ()))

    def list_storms(self) -> list[RealStormState]:
        self._refresh_live_storms()
        self._ensure_cycle_index()
        # Live storms first -- they're what "active storms" genuinely
        # means; archive storms fall outside `_ACTIVE_WINDOW` in every
        # real case today anyway (HURDAT2 tops out at the 2023 season).
        merged = {**self.storms, **self._live_storms}
        return list(merged.values())

    def get_storm(self, storm_id: str) -> RealStormState:
        self._refresh_live_storms()
        self._ensure_cycle_index()
        if storm_id in self._live_storms:
            return self._live_storms[storm_id]
        try:
            return self.storms[storm_id]
        except KeyError as exc:
            raise LookupError(f"unknown storm {storm_id!r}") from exc

    def refresh_registry_if_stale(self) -> None:
        """Re-pull the real registry if the last pull is stale (or there
        hasn't been one yet). Best-effort, same degrade-not-crash contract
        as `_refresh_live_storms`: `ModelRegistry.reload`'s own pull
        already swallows a durable-storage failure internally, so the
        only new failure mode here is resolving a checkpoint store at
        all, which is worth guarding explicitly since a real cycle must
        still run (on whatever registry state it already has) rather than
        500 just because a periodic background refresh couldn't reach
        S3/R2.

        Public (not `_refresh_registry`, its name before this) because
        `api.routers.registry` needs to call it too -- found for real: a
        registry write from outside this process (e.g. `anemoi registry-
        reconcile`, a real one-off registry correction run this session)
        never appeared on a live `/v1/registry` response for up to
        `_REGISTRY_TTL`, since only `run_cycle` ever triggered a refresh.
        Every other registry-reading route was silently serving a stale
        in-memory copy no cycle had happened to refresh yet.
        """
        now = datetime.now(UTC)
        if (
            self._registry_fetched_at is not None
            and now - self._registry_fetched_at < _REGISTRY_TTL
        ):
            return
        try:
            self.registry.reload(self._checkpoint_store)
        except Exception:  # noqa: BLE001 - a stale registry must never block a real cycle
            pass
        self._registry_fetched_at = now

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

        self.refresh_registry_if_stale()
        self._ensure_drift_restored()
        storm = self.get_storm(storm_id)
        target = parse_cycle_label(cycle)
        # `LatencyOracle`/`plan_cycle` have no wall-clock concept of "now" --
        # by design, since a replay harness needs to plan a cycle before it
        # happens using only a hypothetical `as_of`. But this is the one real
        # call site running against real wall-clock time, and without a
        # guard here `plan_cycle` cheerfully "plans" a cycle whose synoptic
        # time hasn't started yet: `LatencyOracle.published_at` always
        # returns `valid_time + latency` regardless of whether that time has
        # actually elapsed, so a future `target` comes back `vitals_estimated
        # =False` -- the real bug this guard closes, found live against
        # EP172026 with a cycle label one full day ahead of real UTC time,
        # which returned `vitals: observed` using a stale position simply
        # relabeled with the future timestamp. A cycle whose target time has
        # already begun (including the one currently in progress, before its
        # real vitals have landed) is unaffected -- that in-progress case is
        # exactly what `vitals_estimated`'s own degraded mode already models
        # honestly.
        now = datetime.now(UTC)
        if target > now:
            raise CycleError(
                f"cycle {cycle} has not started yet (real UTC time is "
                f"{now:%Y-%m-%d %H:%M}Z); a forecast cycle can only be issued "
                "for a synoptic time that has already begun"
            )
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
            plan, fix, deterministic, ensemble,
            coastline=coastline, requested_members=members,
        )
        with self._lock:
            storm.cycles[output.label] = output
            self._record_drift_sample(output)
        # Outside the lock: unlike _record_drift_sample (in-memory only,
        # cheap), this does real disk I/O and a best-effort network upload
        # via CheckpointStore -- holding self._lock across that would block
        # every other request needing it (list_storms/get_storm/run_cycle
        # for an unrelated storm) for as long as a slow/stalled durable
        # store takes to time out. Nothing it does needs the lock: it only
        # reads storm/fix/output (all already-published-by-here values,
        # not shared mutable RealState state) and writes to durable
        # storage, not to any dict this class guards.
        self._record_skew_sample(storm, fix, output)
        self._persist_cycle(storm_id, output)
        self._persist_drift_live()
        return output

    def _persist_cycle(self, storm_id: str, output: CycleOutput) -> None:
        """Best-effort durable copy of the served result (#175), outside the
        lock for the same reason as `_record_skew_sample`: a failed or slow
        write must never fail or stall the cycle itself."""
        from . import convert
        from .cycle_store import save_cycle_result

        try:
            save_cycle_result(self._checkpoint_store, convert.cycle_result_out(storm_id, output))
        except Exception:  # noqa: BLE001 - best-effort, see docstring
            return
        if self._cycle_index is not None:
            self._cycle_index.setdefault(storm_id, set()).add(output.label)

    def _ensure_drift_restored(self) -> None:
        if self._drift_restored:
            return
        from .cycle_store import load_drift_live

        try:
            restored = load_drift_live(self._checkpoint_store)
        except Exception:  # noqa: BLE001 - retried next time; nothing is written back until it works
            return
        with self._lock:
            if self._drift_restored:
                return
            self._drift_restored = True
            if restored is not None:
                features, models = restored
                self._live_env_features = (features + self._live_env_features)[
                    -self._live_env_features_max:
                ]
                self._models_ever_contributed |= models

    def _persist_drift_live(self) -> None:
        from .cycle_store import save_drift_live

        with self._lock:
            if not self._drift_restored:
                return
            features = list(self._live_env_features)
            models = set(self._models_ever_contributed)
        try:
            save_drift_live(self._checkpoint_store, features, models)
        except Exception:  # noqa: BLE001 - best-effort
            pass

    def _record_drift_sample(self, output: CycleOutput) -> None:
        """Real drift-detection bookkeeping (#148) -- called under
        `self._lock` from `run_cycle` itself, not a separate public
        method, since a sample only exists in the context of a real cycle
        that just ran."""
        env_features = output.deterministic.env_features
        if env_features is not None:
            self._live_env_features.append(env_features)
            if len(self._live_env_features) > self._live_env_features_max:
                self._live_env_features = self._live_env_features[-self._live_env_features_max:]
        self._models_ever_contributed.update(output.deterministic.contributors)

    def _record_skew_sample(self, storm: RealStormState, fix: Fix, output: CycleOutput) -> None:
        """Best-effort durable persistence of this cycle's real replay
        inputs (#148's skew half) -- `monitoring.skew_audit
        .record_operational_cycle`'s own docstring covers why this must
        never fail the cycle it's attached to, and why it no-ops (not an
        exception) for a cycle no real model contributed to."""
        from ..monitoring.skew_audit import record_operational_cycle

        try:
            store = self._checkpoint_store
        except Exception:  # noqa: BLE001 - see _get_drift_reference: local-only must still work
            store = None
        try:
            record_operational_cycle(
                storm.storm_id, storm.track, fix, output,
                local_root=self.registry.root, checkpoint_store=store,
            )
        except Exception:  # noqa: BLE001 - best-effort, never fail a cycle over this
            pass

    def get_cycle(self, storm_id: str, cycle: str) -> CycleOutput | schemas.CycleResult:
        storm = self.get_storm(storm_id)
        try:
            return storm.cycles[cycle]
        except KeyError as exc:
            raise LookupError(f"cycle {cycle!r} has not been run for {storm_id!r}") from exc

    # ---- monitoring: drift & skew ---------------------------------------
    #
    # A real bug, not a design choice: `api.routers.monitoring`/`retraining`
    # call `state.drift_report`/`skew_report`/`pending_retrain_jobs`
    # unconditionally, on whatever `state_dependency()` returns -- but this
    # class's own docstring's claim of "the exact same public surface
    # DemoState does" was never actually true for these three. Calling them
    # against a real deployment 500s (an AttributeError with no CORS
    # headers on the error response, which a browser reports as an opaque
    # "TypeError: Load failed" -- found by actually visiting the deployed
    # console's /monitoring page, not assumed).
    #
    # `DemoState`'s versions generate synthetic reference/live distributions
    # from `np.random.default_rng` -- fabricating numbers like that under a
    # *real* deployment would be actively misleading, not just incomplete.
    #
    # Drift is now real (#148): `_record_drift_sample` (called from
    # `run_cycle`) accumulates this process's own real `env_features` per
    # cycle, `_get_drift_reference` lazily loads the real Stage B
    # reference `anemoi drift-reference-fit` fits offline from cached
    # GDAS fields, and `drift_report` below compares them via the real
    # `monitoring.drift.detect_feature_drift`. Still degrades honestly,
    # not by fabricating: `n_live=0` when no reference has been fit yet,
    # a model hasn't contributed to a real cycle yet this process, or
    # fewer than `detect_feature_drift`'s own minimum sample count has
    # been collected.
    #
    # Skew is now real too (#148, 2026-09-22): `_record_skew_sample`
    # (called from `run_cycle`, mirroring `_record_drift_sample`) durably
    # persists each real cycle's replay inputs via `monitoring.skew_audit
    # .record_operational_cycle`; the offline `anemoi skew-audit` CLI
    # (`monitoring.skew_audit.audit_run`) finds every such record old
    # enough for ERA5T to have caught up with and replays it through the
    # same `training.real_inference_cycle.build_real_deterministic_fn`
    # path, just pointed at ERA5T instead of GDAS
    # (`training.real_inference_live.era5t_fields`); `skew_report` below
    # loads whatever real `SkewSample`s that's produced so far and feeds
    # them to the real, unchanged `monitoring.skew.SkewMonitor`. Still
    # degrades honestly, not by fabricating: an empty corpus, or fewer
    # than `SkewMonitor`'s own 8-sample minimum in the rolling 14-day
    # window, reads as `n=0` with an explicit `reasons` entry, not a
    # crash and not a synthetic estimate.

    def _get_drift_reference(self) -> ReferenceDistribution | None:
        """Lazy, at-most-once-per-process load of the real Stage B
        reference `anemoi drift-reference-fit` fit offline -- best-effort,
        same degrade-not-crash contract every other real fetch in this
        module follows. Tried again only if it hasn't been tried at all
        yet this process; a reference that's genuinely missing (nobody's
        fit one yet) doesn't get retried on every single request."""
        if self._drift_reference is not None or self._drift_reference_load_attempted:
            return self._drift_reference
        self._drift_reference_load_attempted = True
        from ..monitoring.reference_store import load_reference

        # Real gap this closes: `self._checkpoint_store` itself raises
        # CheckpointStoreError when no real S3_ARTIFACT_* env is configured
        # (confirmed live -- the same reason run_cycle's own deterministic
        # fallback message mentions it, see #100). A local-only reference
        # (no durable mirror configured at all) is still a real, valid
        # deployment mode -- resolving the store must not prevent even
        # attempting the local read.
        try:
            store = self._checkpoint_store
        except Exception:  # noqa: BLE001 - see above: local-only must still work
            store = None
        try:
            path = Path(self.registry.root) / "drift_reference.json"
            self._drift_reference = load_reference(path, store)
        except Exception:  # noqa: BLE001 - a missing/broken reference must never crash a cycle
            self._drift_reference = None
        return self._drift_reference

    def drift_report(self, model: str) -> DriftReport:
        self._ensure_drift_restored()
        reference = self._get_drift_reference()
        if reference is None or model not in self._models_ever_contributed:
            return DriftReport(features=(), n_live=0)
        live = np.array(self._live_env_features)
        try:
            return detect_feature_drift(reference, live)
        except DriftError:
            # Fewer than detect_feature_drift's own minimum (currently 30)
            # real samples collected so far this process -- an honest
            # empty report with the real count, not a fabricated one.
            return DriftReport(features=(), n_live=live.shape[0])

    def _get_skew_samples(self) -> list[SkewSample]:
        """Real skew corpus (#148), lazily loaded and TTL-refreshed from
        durable storage -- see `_SKEW_SAMPLES_TTL`'s own docstring for why
        this differs from the drift reference's load-once-per-process
        pattern."""
        now = datetime.now(UTC)
        if (
            self._skew_samples is not None
            and self._skew_samples_fetched_at is not None
            and now - self._skew_samples_fetched_at < _SKEW_SAMPLES_TTL
        ):
            return self._skew_samples
        from ..monitoring.skew_audit import load_skew_samples

        try:
            store = self._checkpoint_store
        except Exception:  # noqa: BLE001 - see _get_drift_reference: local-only must still work
            store = None
        try:
            # Must match monitoring.skew_audit.audit_run's own samples_path
            # (Path(local_root) / "skew" / "skew_samples.json") -- a real
            # bug this fixes: this used to read registry_root/skew_samples
            # .json (no "skew/" subdirectory), a path audit_run never
            # wrote to, so a durable-store hiccup (or no store configured
            # at all) would always degrade to an empty corpus even with a
            # real local file sitting one directory over.
            path = Path(self.registry.root) / "skew" / "skew_samples.json"
            samples = load_skew_samples(path, store)
            if not samples and not path.exists():
                # Best-effort fallback to the pre-fix flat path, in case a
                # local skew-audit run already wrote there against an
                # older build of this code -- never the primary source of
                # truth, just avoids silently losing a real local corpus.
                legacy_path = Path(self.registry.root) / "skew_samples.json"
                if legacy_path.exists():
                    samples = load_skew_samples(legacy_path)
            self._skew_samples = samples
        except Exception:  # noqa: BLE001 - a missing/broken corpus must never crash a cycle
            self._skew_samples = self._skew_samples or []
        self._skew_samples_fetched_at = now
        return self._skew_samples

    def skew_report(self, *, lead_hours: int = 48) -> SkewReport:
        now = datetime.now(UTC)
        samples = self._get_skew_samples()
        if not samples:
            return SkewReport(
                lead_hours=lead_hours, n=0, window_start=now, window_end=now,
                mean_track_delta_nm=0.0, mean_abs_intensity_delta_kt=0.0, intensity_bias_kt=0.0,
                alert=False,
                reasons=(
                    "no real ERA5T-vs-operational skew samples yet (anemoi "
                    "skew-audit hasn't found any real operational cycles old "
                    "enough to audit)",
                ),
            )
        monitor = SkewMonitor()
        for sample in samples:
            monitor.record(sample)
        report = monitor.report(now, lead_hours=lead_hours)
        if report is None:
            return SkewReport(
                lead_hours=lead_hours, n=0, window_start=now, window_end=now,
                mean_track_delta_nm=0.0, mean_abs_intensity_delta_kt=0.0, intensity_bias_kt=0.0,
                alert=False,
                reasons=(
                    f"fewer than {monitor.min_samples} real skew samples in the "
                    f"rolling {monitor.window.days}-day window yet",
                ),
            )
        return report

    def pending_retrain_jobs(self) -> list[RetrainJob]:
        """Real retraining triggers (§5.5), now genuinely detecting two
        real signals instead of always returning empty:

        - **Per-model drift** (#148's drift half): `drift_report(model)
          .alert` for every real model that has contributed to at least
          one real cycle this process's lifetime.
        - **Champion/latent desync** (§5.7, GitHub #149):
          `ModelRegistry.desynced_derived_models` -- real, live drift
          between fusion/diffusion's recorded `latent_signature` and the
          *current* Group 1 champion set, the exact "recovery path is
          structurally weak" gap #149 documented: nothing previously
          noticed or surfaced a desync caused by `registry-reconcile`
          re-staging an already-registered version (as opposed to a fresh
          retrain, which the existing CASCADE path already covers).

        Real skew is deliberately **not** mapped to a specific model here
        -- the same restraint `cli.cmd_retrain_check`'s own docstring
        already explains: a real skew alert is system-wide (one paired
        ERA5T-vs-operational comparison of the whole deterministic stack),
        not per-model, and nothing in this codebase's scope says which
        model(s) it should retrigger. A real skew alert is still visible
        directly via `skew_report()`/`GET /v1/monitoring/skew`; guessing a
        mapping here would be exactly the kind of fabrication this
        module's monitoring section already refuses to do elsewhere.

        This surfaces a real desync -- it does not auto-dispatch a
        retrain. `cli.cmd_retrain_check` only ever auto-dispatches
        calendar/data-volume triggers today (its own docstring: "a real
        dispatcher for [drift/skew/cascade] is separate, scoped future
        work"); `LATENT_DESYNC` gets the identical treatment for
        consistency, not a lesser one -- auto-launching unattended GPU
        retraining specifically for this trigger remains real, separate
        future work (Decision Log).
        """
        from ..training.triggers import SeasonState, evaluate_all

        drifted = tuple(m for m in ALL_MODELS if self.drift_report(m).alert)
        desynced = self.registry.desynced_derived_models()
        active_storms = tuple(s.storm_id for s in self.list_storms() if s.active)
        return evaluate_all(
            datetime.now(UTC), SeasonState(active_storms=active_storms),
            drifted_models=drifted, desynced_models=desynced,
        )


_REAL_STATE: RealState | None = None
_REAL_STATE_LOCK = threading.Lock()


def get_real_state() -> RealState:
    global _REAL_STATE
    if _REAL_STATE is None:
        with _REAL_STATE_LOCK:
            if _REAL_STATE is None:
                _REAL_STATE = RealState()
    return _REAL_STATE
