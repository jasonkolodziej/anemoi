"""Who may run which cycle, and when (#212).

A cycle label is one shared, public forecast: every visitor sees the stored
result as "the latest run". Before this, any logged-in user's POST replaced
it -- with their own position/wind overrides, a one-member ensemble, or a
label years outside the storm -- and a manual run of the current label made
the scheduled run skip that storm, so the official cycle was whatever the
user had run, possibly on estimated vitals the t+1:30 schedule exists to
avoid. Two runs of the same label could also execute at once (a manual POST
racing the Workflow, or a Workflow retry racing its own lost first attempt),
the last to finish winning in R2 and KV.

The rules, enforced by `RealState.run_cycle` (the demo state has no cron and
no shared audience, so it keeps running anything):

* **Scheduled** runs (the cycle Workflow, ``X-Anemoi-Run-Source: scheduled``,
  a header the public Worker route strips) are the official cycle. One that
  finds a scheduled result already stored is refused as ``exists``; one that
  finds a manual result replaces it.
* **Manual** runs only fill a label nothing has run. An existing label is
  refused as ``exists`` unless an operator (``ANEMOI_OPERATOR_USER_IDS``)
  asks to ``replace`` it. For an active storm, a manual run of a label whose
  scheduled run hasn't happened yet is refused as ``not_scheduled_yet`` --
  the cron runs it at t + ``cycle.scheduled_run_offset_minutes``.
* Every run's label must fall within the storm's own track: no earlier than
  its first fix, no later than `LIFETIME_GRACE` past its latest one.
* At most one run per (storm, label) executes at a time; a second is refused
  as ``in_progress`` (the Workflow retries those; a user sees why).
"""

from __future__ import annotations

import os
import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..inference.cycle import CycleError, RunInfo
from ..inference.scheduler import SCHEDULED_RUN_OFFSET
from ..time_utils import cycle_label

SCHEDULED = "scheduled"
MANUAL = "manual"
RUN_SOURCES = (SCHEDULED, MANUAL)

#: Request header the cycle Workflow sets on its container calls. The public
#: Worker route deletes it, so only the Workflow (which calls the container
#: directly) can send it.
RUN_SOURCE_HEADER = "X-Anemoi-Run-Source"
#: Set in the API image: a manual cycle POST must carry the user id the
#: Worker resolved. Unset for local and demo use, where nothing resolves one.
REQUIRE_CALLER_ENV = "ANEMOI_REQUIRE_CALLER"
#: Comma-separated user ids allowed to re-run an existing cycle.
OPERATORS_ENV = "ANEMOI_OPERATOR_USER_IDS"
#: How far past a storm's latest fix a cycle may be: the current synoptic
#: label is up to 6 h past the latest fix before its vitals land, and one
#: missed bulletin makes that 12 h. Anything later is not this storm's cycle.
LIFETIME_GRACE = timedelta(hours=12)


class CycleConflict(RuntimeError):
    """A run refused by policy rather than by bad input -- served as 409 with
    a machine-readable ``code`` the cycle Workflow branches on."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class RunRequest:
    """Who is asking for a run, as the router resolved it from the request."""

    source: str = MANUAL
    user_id: str | None = None
    replace: bool = False
    #: Request fields that moved the inputs off the operational defaults.
    overrides: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.source not in RUN_SOURCES:
            raise ValueError(f"unknown run source {self.source!r}")

    @property
    def operator(self) -> bool:
        return self.user_id is not None and self.user_id in operator_ids()

    def info(self) -> RunInfo:
        return RunInfo(source=self.source, overrides=self.overrides)


def operator_ids() -> frozenset[str]:
    raw = os.environ.get(OPERATORS_ENV, "")
    return frozenset(part.strip() for part in raw.split(",") if part.strip())


def stored_source(existing: object) -> str:
    """The run source of a stored cycle -- a `CycleOutput` this process ran,
    or a `schemas.CycleResult` read back from R2. A result stored before
    #212 carries none; those count as official (scheduled), so a scheduled
    run never silently replaces history it can't classify."""
    run = getattr(existing, "run", None)
    source = getattr(run, "source", None)
    return source if source in RUN_SOURCES else SCHEDULED


def check_run(
    *,
    storm_id: str,
    target: datetime,
    first_fix: datetime,
    latest_fix: datetime,
    active: bool,
    cycles: Mapping[str, object],
    request: RunRequest,
    now: datetime,
) -> None:
    """Raise `CycleConflict` (or `CycleError` for a label outside the storm)
    if ``request`` may not run ``target`` for this storm right now."""
    label = cycle_label(target)
    if target < first_fix or target > latest_fix + LIFETIME_GRACE:
        raise CycleError(
            f"cycle {label} is outside {storm_id}'s track "
            f"({cycle_label(first_fix)} to {cycle_label(latest_fix)}); a cycle must "
            f"start between its first fix and {int(LIFETIME_GRACE.total_seconds() // 3600)} h "
            "after its latest"
        )

    # Membership by key listing, not `in`: Mapping.__contains__ reads the
    # value, and a stored result R2 can't return right now would then look
    # absent and be overwritten.
    if label in set(cycles):
        existing_source = _existing_source(cycles, label)
        if request.source == SCHEDULED:
            if existing_source == SCHEDULED:
                raise CycleConflict("exists", f"the scheduled {label} cycle for {storm_id} has already run")
            return  # the official run replaces a manual one
        if not (request.replace and request.operator):
            raise CycleConflict(
                "exists",
                f"{storm_id} already has a {label} cycle ({existing_source} run); "
                "pick it from Past cycles instead of running it again",
            )
        return

    if request.source == MANUAL and active and not request.operator:
        due = target + SCHEDULED_RUN_OFFSET
        if now < due:
            raise CycleConflict(
                "not_scheduled_yet",
                f"the {label} cycle runs automatically at {due:%H:%M}Z, once its "
                "vitals have landed; a manual run before then would replace it",
            )


def _existing_source(cycles: Mapping[str, object], label: str) -> str:
    try:
        return stored_source(cycles[label])
    except KeyError:
        # Listed in the index but unreadable right now (R2 hiccup): assume
        # the official run is there rather than overwrite it blind.
        return SCHEDULED


class InFlight:
    """Per-(storm, label) single-flight guard for cycle runs."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._running: set[tuple[str, str]] = set()

    @contextmanager
    def hold(self, storm_id: str, label: str) -> Iterator[None]:
        key = (storm_id, label)
        with self._lock:
            if key in self._running:
                raise CycleConflict(
                    "in_progress", f"the {label} cycle for {storm_id} is already running",
                )
            self._running.add(key)
        try:
            yield
        finally:
            with self._lock:
                self._running.discard(key)
