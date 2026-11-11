"""Forecast cycle scheduling.

Scope v2.1 §6.2.2 and §8.2. The cycle is *gated on the working fix*, not on the
synoptic time: prefetch runs from t+0:00 against already-staged t-6 NWP fields,
but the cycle formally starts when TC-Vitals lands (nominally t+0:45, timeout
t+1:20 -- derived, see :func:`derive_vitals_timeout`; the scope's t+1:30 did not
survive the arithmetic). The deliverable deadline is the NHC advisory at t+3:00.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from .. import config
from ..data.availability import (
    AvailabilityOracle,
    CycleInputs,
    resolve_cycle_inputs,
)
from ..time_utils import (
    ADVISORY_OFFSET,
    MAX_NWP_LAG_HOURS,
    advisory_time,
    cycle_label,
    require_synoptic,
)

#: Nominal working-fix arrival.
NOMINAL_VITALS_OFFSET = timedelta(
    minutes=config.get("inference", "cycle.nominal_vitals_offset_minutes", int)
)

#: Safety margin required between product delivery and the advisory.
ADVISORY_MARGIN = timedelta(minutes=config.get("inference", "cycle.advisory_margin_minutes", int))


class Stage(str, Enum):
    ASSEMBLY = "assembly"
    PREPROCESS = "preprocess"
    DETERMINISTIC = "deterministic"
    FUSION = "fusion"
    DIFFUSION = "diffusion"
    POSTPROCESS = "postprocess"


@dataclass(frozen=True, slots=True)
class StageBudget:
    stage: Stage
    target: timedelta
    maximum: timedelta

    def __post_init__(self) -> None:
        if self.maximum < self.target:
            raise ValueError(f"{self.stage.value}: max budget below target")


def _budgets(profile: str) -> tuple[StageBudget, ...]:
    """inference.yaml ``budgets.<profile>``: every stage, in pipeline order."""
    out = []
    for stage in Stage:
        target = config.get("inference", f"budgets.{profile}.{stage.value}.target", int)
        maximum = config.get("inference", f"budgets.{profile}.{stage.value}.max", int)
        try:
            out.append(StageBudget(stage, timedelta(minutes=target), timedelta(minutes=maximum)))
        except ValueError as exc:
            where = f"inference.yaml: budgets.{profile}.{stage.value}"
            raise config.ConfigError(f"{where}: {exc}") from exc
    extra = set(config.get("inference", f"budgets.{profile}", dict)) - {s.value for s in Stage}
    if extra:
        raise config.ConfigError(
            f"inference.yaml: budgets.{profile} has unknown stages {sorted(extra)}"
        )
    return tuple(out)


#: The §6.2.2 table (inference.yaml ``budgets.standard``). Durations are
#: measured from cycle start.
DEFAULT_BUDGETS: tuple[StageBudget, ...] = _budgets("standard")

#: Load-shedding profile (inference.yaml ``budgets.reduced``). Used when the
#: standard profile would not clear the advisory -- typically after a late
#: working fix. The saving comes almost entirely from Anemoi-Spread:
#: REDUCED_ENSEMBLE_MEMBERS instead of DEFAULT_ENSEMBLE_MEMBERS. A smaller
#: ensemble is a real loss of tail resolution, but it is a smaller loss than
#: delivering nothing before the advisory goes out.
REDUCED_BUDGETS: tuple[StageBudget, ...] = _budgets("reduced")

#: Ensemble member counts by profile (inference.yaml ``ensemble.members`` /
#: ``ensemble.reduced_members``).
#:
#: 50, not 20 (#188). Every §6.1 product is a quantile or a fraction estimated
#: from these draws -- the cone radius is the 67th percentile of member
#: distance, the intensity band is p10/p90, landfall and RI are member
#: fractions -- so the member count sets the precision of all four, and the
#: smallest probability expressible at all is 1/n. At 20 the served numbers
#: carried real sampling noise: a true 62 nm cone radius reads 48-76 nm, a
#: true 109 kt p90 reads 99-116 kt (crossing a Saffir-Simpson boundary), and
#: no probability below 5% can be represented.
#:
#: It also biased `monitoring.calibration_audit`: a *perfectly* calibrated
#: ensemble measures 62.1% containment at n=20 against a 67% nominal, because
#: the cone is centred on the ensemble mean (itself off by ~sigma/sqrt(n))
#: and its radius is a 20-sample percentile. That -4.9 point error is a third
#: of `_VERDICT_MARGIN`, and it leans "too narrow" -- the same direction #166
#: has been chasing. At 50 it falls to -2.3.
#:
#: Affordable because `TrajectoryDenoiser.sample` carries members as a batch
#: dimension: one forward pass per denoising step regardless of count.
#: Measured at production architecture, 20 -> 50 costs 0.06s -> 0.09s, and
#: even at 16x the model size it is under 2s against the 13-minute §6.2.2
#: diffusion budget. The budget is spent on Group 1 forward passes and input
#: fetches, not on ensemble size. `Inference-Cycle`'s own stage table already
#: contemplated "20 members; 50 relaxed".
DEFAULT_ENSEMBLE_MEMBERS: int = config.get("inference", "ensemble.members", int)
#: Scaled with the default to preserve the 2:1 shed ratio the original design
#: chose (#8). Note this lever buys far less wall time than it appears to --
#: see the batching note above -- which is worth revisiting on its own.
REDUCED_ENSEMBLE_MEMBERS: int = config.get("inference", "ensemble.reduced_members", int)
if not 0 < REDUCED_ENSEMBLE_MEMBERS <= DEFAULT_ENSEMBLE_MEMBERS:
    raise config.ConfigError(
        "inference.yaml: ensemble.reduced_members must be between 1 and "
        f"ensemble.members ({DEFAULT_ENSEMBLE_MEMBERS}), got {REDUCED_ENSEMBLE_MEMBERS}"
    )


def total_budget(budgets=DEFAULT_BUDGETS, *, worst_case: bool = False) -> timedelta:
    return sum(
        (b.maximum if worst_case else b.target for b in budgets),
        timedelta(),
    )


def derive_vitals_timeout(
    budgets: tuple[StageBudget, ...] = REDUCED_BUDGETS,
    *,
    margin: timedelta = ADVISORY_MARGIN,
) -> timedelta:
    """Latest cycle start that still clears the advisory on the worst-case path.

    Scope v2.1 §6.2.2 wrote the timeout as a flat t+1:30. That number does not
    survive the arithmetic: with the reduced profile's 70-minute worst case and
    a 30-minute advisory margin, a 1:30 start finishes at t+2:40 and leaves only
    20 minutes. Deriving the timeout from the budget keeps the three numbers
    consistent when any one of them is retuned, rather than leaving a latent
    10-minute shortfall in a table.
    """
    return ADVISORY_OFFSET - total_budget(budgets, worst_case=True) - margin


#: The point past which we stop waiting for the working fix (t+1:20).
VITALS_TIMEOUT = derive_vitals_timeout()

# inference.yaml writes the timeout down so a reader sees it, but it is
# derived, never chosen: a file whose number disagrees with its own budgets
# is refused rather than trusted -- hardcoding it is how the original
# 10-minute shortfall got in (Decision Log #11).
_configured_timeout = config.get("inference", "cycle.vitals_timeout_minutes", int)
if _configured_timeout != VITALS_TIMEOUT / timedelta(minutes=1):
    raise config.ConfigError(
        "inference.yaml: cycle.vitals_timeout_minutes must equal advisory_offset - "
        "reduced worst case - advisory_margin = "
        f"{VITALS_TIMEOUT / timedelta(minutes=1):g} for these budgets"
    )

#: When production actually runs each cycle (inference.yaml
#: ``cycle.scheduled_run_offset_minutes``): anemoi-api-real's cron, which the
#: Python side doesn't schedule but must not contradict -- a run before the
#: vitals timeout could start on vitals that were still on their way.
SCHEDULED_RUN_OFFSET = timedelta(
    minutes=config.get("inference", "cycle.scheduled_run_offset_minutes", int)
)
if SCHEDULED_RUN_OFFSET <= VITALS_TIMEOUT:
    raise config.ConfigError(
        "inference.yaml: cycle.scheduled_run_offset_minutes must be after the "
        f"vitals timeout ({VITALS_TIMEOUT / timedelta(minutes=1):g} min)"
    )


@dataclass(frozen=True, slots=True)
class ScheduledStage:
    stage: Stage
    start: datetime
    end_target: datetime
    end_max: datetime


@dataclass(frozen=True, slots=True)
class CyclePlan:
    """A concrete plan for one forecast cycle."""

    target_time: datetime
    cycle_start: datetime
    stages: tuple[ScheduledStage, ...]
    inputs: CycleInputs
    vitals_estimated: bool
    #: True when the reduced-ensemble profile was selected to hold the deadline.
    load_shed: bool = False

    @property
    def label(self) -> str:
        return cycle_label(self.target_time)

    @property
    def core_ready_target(self) -> datetime:
        return self._stage(Stage.FUSION).end_target

    @property
    def core_ready_max(self) -> datetime:
        return self._stage(Stage.FUSION).end_max

    @property
    def spread_ready_target(self) -> datetime:
        return self.stages[-1].end_target

    @property
    def spread_ready_max(self) -> datetime:
        return self.stages[-1].end_max

    @property
    def advisory_deadline(self) -> datetime:
        return advisory_time(self.target_time)

    @property
    def margin_target(self) -> timedelta:
        return self.advisory_deadline - self.spread_ready_target

    @property
    def margin_max(self) -> timedelta:
        return self.advisory_deadline - self.spread_ready_max

    @property
    def meets_advisory_deadline(self) -> bool:
        """True if even the worst-case path clears the advisory with margin."""
        return self.margin_max >= ADVISORY_MARGIN

    @property
    def degraded(self) -> bool:
        return self.vitals_estimated or self.load_shed or self.inputs.degraded

    @property
    def requested_ensemble_members(self) -> int:
        """Ensemble member count the cycle should request from Anemoi-Spread.

        This is what ``load_shed`` actually controls: the flag alone changes
        nothing downstream unless something reads it. ``run_cycle`` passes
        this to the ensemble generator so the reduced profile's time savings
        (REDUCED_BUDGETS) are real rather than just a schedule on paper.
        """
        return REDUCED_ENSEMBLE_MEMBERS if self.load_shed else DEFAULT_ENSEMBLE_MEMBERS

    def _stage(self, stage: Stage) -> ScheduledStage:
        for s in self.stages:
            if s.stage is stage:
                return s
        raise KeyError(stage)

    def describe(self) -> str:
        lines = [
            f"cycle {self.label}  start {self.cycle_start:%H:%M}Z"
            f"  nwp t-{self.inputs.nwp.lag_hours}h"
            + ("  [DEGRADED]" if self.degraded else "")
        ]
        for s in self.stages:
            lines.append(
                f"  {s.stage.value:<14} {s.start:%H:%M} -> "
                f"{s.end_target:%H:%M} (max {s.end_max:%H:%M})"
            )
        lines.append(
            f"  advisory {self.advisory_deadline:%H:%M}Z  "
            f"margin {int(self.margin_max.total_seconds() // 60)} min worst case"
        )
        return "\n".join(lines)


class CycleAbandoned(RuntimeError):
    """The cycle cannot run: a required input never arrived."""


def plan_cycle(
    t: datetime,
    oracle: AvailabilityOracle,
    *,
    budgets: tuple[StageBudget, ...] = DEFAULT_BUDGETS,
    vitals_timeout: timedelta = VITALS_TIMEOUT,
    allow_estimated_vitals: bool = config.get("inference", "cycle.allow_estimated_vitals", bool),
    allow_load_shedding: bool = config.get("inference", "cycle.allow_load_shedding", bool),
    max_nwp_lag_hours: int = MAX_NWP_LAG_HOURS,
) -> CyclePlan:
    """Build the plan for forecast cycle ``t``.

    Cycle start is the later of the working-fix arrival and the NWP staging
    time, capped at ``t + vitals_timeout``. Past the cap the cycle runs on an
    extrapolated vitals estimate and the product carries ``vitals=estimated``
    (§6.2.2 degraded modes) -- late is worse than approximate, because an
    advisory published without our guidance is worth nothing.
    """
    require_synoptic(t)
    timeout_at = t + vitals_timeout

    vitals_pub = oracle.published_at("besttrack_working", t)
    vitals_estimated = vitals_pub is None or vitals_pub > timeout_at
    if vitals_estimated and not allow_estimated_vitals:
        raise CycleAbandoned(
            f"working fix for {cycle_label(t)} not available by "
            f"{timeout_at:%H:%M}Z and estimation is disabled"
        )

    cycle_start = timeout_at if vitals_estimated else max(vitals_pub, t)
    inputs = resolve_cycle_inputs(
        t, cycle_start, oracle, max_nwp_lag_hours=max_nwp_lag_hours
    )

    nwp_status = inputs.status("gdas_gfs")
    if not nwp_status.available:
        raise CycleAbandoned(
            f"no NWP cycle within {max_nwp_lag_hours}h for {cycle_label(t)}; "
            "fall back to LSTM + climatology mode (Scope v2.1 §4.6.4)"
        )

    deadline = advisory_time(t) - ADVISORY_MARGIN
    load_shed = False
    if allow_load_shedding and cycle_start + total_budget(budgets, worst_case=True) > deadline:
        # The standard profile cannot hold the advisory from this start time.
        # Shed ensemble members rather than deliver late (§6.2.2 degraded modes).
        budgets = REDUCED_BUDGETS
        load_shed = True

    return CyclePlan(
        target_time=t,
        cycle_start=cycle_start,
        stages=_schedule_stages(cycle_start, budgets),
        inputs=inputs,
        vitals_estimated=vitals_estimated,
        load_shed=load_shed,
    )


def _schedule_stages(
    cycle_start: datetime, budgets: tuple[StageBudget, ...]
) -> tuple[ScheduledStage, ...]:
    stages: list[ScheduledStage] = []
    target_cursor = max_cursor = cycle_start
    for budget in budgets:
        stages.append(
            ScheduledStage(
                stage=budget.stage,
                start=target_cursor,
                end_target=target_cursor + budget.target,
                end_max=max_cursor + budget.maximum,
            )
        )
        target_cursor += budget.target
        max_cursor += budget.maximum
    return tuple(stages)


def plan_day(
    day_start: datetime,
    oracle: AvailabilityOracle,
    **kwargs,
) -> list[CyclePlan]:
    """Plan all four cycles of a day, skipping any that must be abandoned."""
    require_synoptic(day_start)
    plans: list[CyclePlan] = []
    for i in range(4):
        t = day_start + timedelta(hours=6 * i)
        try:
            plans.append(plan_cycle(t, oracle, **kwargs))
        except CycleAbandoned:
            continue
    return plans
