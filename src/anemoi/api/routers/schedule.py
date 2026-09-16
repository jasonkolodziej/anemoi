"""Cycle scheduling -- the HTTP equivalent of ``anemoi schedule``."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, status

from ...data.availability import LatencyOracle
from ...inference.scheduler import plan_day
from .. import convert, schemas

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.get("", response_model=schemas.ScheduleOut)
def schedule(
    date: str = Query(..., description="UTC date, YYYY-MM-DD", examples=["2026-08-06"]),
    worst_case: bool = Query(False, description="Use max latencies instead of typical"),
) -> schemas.ScheduleOut:
    try:
        day_start = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"invalid date: {exc}") from exc

    oracle = LatencyOracle(use_max_latency=worst_case)
    plans = plan_day(day_start, oracle)
    return schemas.ScheduleOut(
        date=date, worst_case=worst_case, plans=[convert.cycle_plan_out(p) for p in plans]
    )
