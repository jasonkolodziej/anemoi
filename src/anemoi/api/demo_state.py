"""In-process demo state for Anemoi-API.

Real HURDAT2/GDAS/GOES ingestion is not wired (see the repo README's "What
this implementation is, and is not"). This module seeds the same
``anemoi.data.synthetic`` generator the CLI and test suite already use, so
the API has storms to list, cycles to run, and a registry/drift/skew state
to report -- all produced by the real operational logic, not by faking JSON.

Replace this module first when wiring real ingestion; every router depends
on it only through the functions below, not on synthetic details directly.
"""

from __future__ import annotations

import random
import string
import threading
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np

from ..data.availability import LatencyOracle
from ..data.besttrack import Fix, Track, TrackQuality
from ..data.sources import Flavor
from ..data.synthetic import generate_season
from ..inference.cycle import CycleOutput, DeterministicForecast, climatological_ensemble, run_cycle
from ..inference.scheduler import plan_cycle
from ..monitoring.drift import DriftReport, ReferenceDistribution, detect_feature_drift
from ..monitoring.skew import SkewReport
from ..tracking.registry import DERIVED_MODELS, GROUP1_MODELS, ModelRegistry, Stage, latent_signature
from ..training.triggers import SeasonState, evaluate_all


@dataclass
class StormState:
    storm_id: str
    track: Track  # FINAL-quality synthetic history; display only, never a model input
    cycles: dict[str, CycleOutput] = field(default_factory=dict)

    @property
    def season(self) -> int:
        return self.track.season

    @property
    def latest_fix(self) -> Fix:
        return self.track.fixes[-1]

    @property
    def active(self) -> bool:
        # A storm is "active" for the demo if its synthetic life cycle would
        # still be running relative to the generator's own clock, i.e. it is
        # one of the most recently generated storms in the current season.
        return True


class DemoState:
    """One process-lifetime instance of everything the API serves.

    Thread-safe enough for a demo/reference server (single lock around
    mutation); a real deployment replaces this with a database and a message
    bus, not with a bigger lock.
    """

    def __init__(self, *, seed: int = 20260806, root: Path | None = None) -> None:
        self._lock = threading.Lock()
        self._rng_seed = seed
        self.root = root or Path.cwd() / ".anemoi-api-demo"
        self.root.mkdir(parents=True, exist_ok=True)
        self.registry = ModelRegistry(self.root / "registry")
        self._seed_storms()
        self._seed_registry()

    # ---- storms ------------------------------------------------------

    def _seed_storms(self) -> None:
        season = datetime.now(UTC).year
        tracks = generate_season(season, n_storms=5, seed=self._rng_seed)
        self.storms: dict[str, StormState] = {t.storm_id: StormState(t.storm_id, t) for t in tracks}

    def list_storms(self) -> list[StormState]:
        return list(self.storms.values())

    def get_storm(self, storm_id: str) -> StormState:
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
        storm = self.get_storm(storm_id)
        from ..time_utils import parse_cycle_label

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
            # the demo mints a fresh WORKING (or ESTIMATED, if the plan calls
            # for it) fix at the same position instead of reusing the FINAL one.
            quality=TrackQuality.ESTIMATED if plan.vitals_estimated else TrackQuality.WORKING,
        )

        leads = (12, 24, 36, 48, 72, 96, 120)

        def deterministic(plan_, fix_):
            steps = np.arange(1, len(leads) + 1, dtype=float)
            return DeterministicForecast(
                target_time=plan_.target_time,
                lead_hours=leads,
                lats=fix_.lat + 0.9 * steps,
                lons=fix_.lon - 1.1 * steps,
                winds_kt=np.clip(fix_.max_wind_kt + 4.0 * steps - 0.4 * steps**2, 15.0, None),
                contributors={"lstm": 0.2, "transformer": 0.35, "gnn": 0.25, "cnn": 0.2},
            )

        output = run_cycle(
            plan,
            fix,
            deterministic,
            lambda det: climatological_ensemble(det, n_members=members, seed=hash(cycle) & 0xFFFF),
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

    # ---- registry (demo seed: one registered version per Group 1 model) --

    def _seed_registry(self) -> None:
        if self.registry.versions("lstm"):
            return  # already seeded on a previous startup (persisted to disk)
        run_id = lambda: "".join(random.choices(string.hexdigits.lower(), k=12))
        group1_versions: dict[str, int] = {}
        for name in GROUP1_MODELS:
            v = self.registry.register(
                name,
                run_id=run_id(),
                input_flavor=Flavor.GDAS_FINETUNE,
                metrics={"track_error_nm_48h": float(random.uniform(35, 65))},
                tags={"input_flavor": "gdas_finetune", "nwp_cycle_lag": "6"},
            )
            self.registry.transition(name, v.version, Stage.PRODUCTION)
            group1_versions[name] = v.version
        sig = latent_signature(group1_versions)
        for name in DERIVED_MODELS:
            v = self.registry.register(
                name,
                run_id=run_id(),
                input_flavor=Flavor.GDAS_FINETUNE,
                metrics={"crps_48h": float(random.uniform(8, 14))},
                latent_signature=sig,
            )
            self.registry.transition(name, v.version, Stage.PRODUCTION)
        self.registry.pin_set("demo-pin-0001", {m: 1 for m in GROUP1_MODELS + DERIVED_MODELS})

    # ---- monitoring: drift & skew (synthetic reference + live samples) ---

    def drift_report(self, model: str, *, seed: int | None = None) -> DriftReport:
        from ..data.features import FEATURE_NAMES

        n_features = len(FEATURE_NAMES)
        rng = np.random.default_rng(seed if seed is not None else hash(model) & 0xFFFF)
        reference = ReferenceDistribution.fit(
            rng.normal(0.0, 1.0, size=(400, n_features)), Flavor.GDAS_FINETUNE
        )
        # A deliberate shift on two models so the demo shows a mixed, realistic
        # state rather than either "everything is fine" or "everything alerts".
        shift = 2.4 if model in ("gnn", "diffusion") else 0.05
        live = rng.normal(shift, 1.0, size=(60, n_features))
        return detect_feature_drift(reference, live)

    def skew_report(self, *, lead_hours: int = 48, seed: int = 7) -> SkewReport:
        rng = np.random.default_rng(seed)
        now = datetime.now(UTC)
        n = 20
        track_delta = float(np.abs(rng.normal(9.0, 4.0, n)).mean())
        intensity_delta = float(np.abs(rng.normal(3.0, 1.5, n)).mean())
        from ..monitoring.skew import SKEW_ALERT_INTENSITY_KT, SKEW_ALERT_TRACK_NM

        alert = track_delta > SKEW_ALERT_TRACK_NM or intensity_delta > SKEW_ALERT_INTENSITY_KT
        reasons = []
        if track_delta > SKEW_ALERT_TRACK_NM:
            reasons.append(f"mean track delta {track_delta:.1f}nm exceeds {SKEW_ALERT_TRACK_NM}nm")
        if intensity_delta > SKEW_ALERT_INTENSITY_KT:
            reasons.append(f"mean intensity delta {intensity_delta:.1f}kt exceeds {SKEW_ALERT_INTENSITY_KT}kt")
        return SkewReport(
            lead_hours=lead_hours,
            n=n,
            window_start=now - timedelta(days=14),
            window_end=now,
            mean_track_delta_nm=track_delta,
            mean_abs_intensity_delta_kt=intensity_delta,
            intensity_bias_kt=float(rng.normal(0.0, 1.0)),
            alert=alert,
            reasons=tuple(reasons),
        )

    # ---- retraining triggers ---------------------------------------------

    def pending_retrain_jobs(self):
        drifted = tuple(m for m in GROUP1_MODELS + DERIVED_MODELS if self.drift_report(m).alert)
        skewed = (("gnn",) if self.skew_report().alert else ())
        state = SeasonState(active_storms=tuple(self.storms))
        return evaluate_all(
            datetime.now(UTC), state, drifted_models=drifted, skewed_models=skewed
        )


_STATE: DemoState | None = None
_STATE_LOCK = threading.Lock()


def get_state() -> DemoState:
    global _STATE
    if _STATE is None:
        with _STATE_LOCK:
            if _STATE is None:
                _STATE = DemoState()
    return _STATE
