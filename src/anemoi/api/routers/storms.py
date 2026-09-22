"""Storms, and running/retrieving forecast cycles against them.

Storm state here is the demo seed layer (``anemoi.api.demo_state``): synthetic
FINAL-quality tracks for display, with each ``POST .../cycles`` call minting a
fresh WORKING/ESTIMATED fix and running the real ``anemoi.inference.cycle.run_cycle``
against it. Swap ``DemoState`` for a real ingestion-backed store and every
route below is unchanged.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ...data.atcf import TRAINED_BASINS, storm_basin
from ...inference.cycle import CycleError
from .. import convert, schemas
from ..deps import require_api_key, state_dependency

router = APIRouter(prefix="/storms", tags=["storms"], dependencies=[Depends(require_api_key)])


def _storm_summary(storm, cycle: str | None = None) -> schemas.StormSummary:
    last = max(storm.cycles) if storm.cycles else None
    basin = storm_basin(storm.storm_id)
    return schemas.StormSummary(
        storm_id=storm.storm_id,
        season=storm.season,
        active=storm.active,
        latest_fix=schemas.FixOut(
            valid_time=storm.latest_fix.valid_time,
            lat=storm.latest_fix.lat,
            lon=storm.latest_fix.lon,
            max_wind_kt=storm.latest_fix.max_wind_kt,
            min_pressure_mb=storm.latest_fix.min_pressure_mb,
            quality=storm.latest_fix.quality.value,
        ),
        peak_wind_kt=storm.track.peak_wind_kt,
        last_cycle=last,
        basin=basin,
        trained_basin=basin in TRAINED_BASINS,
    )


@router.get("", response_model=list[schemas.StormSummary])
def list_storms(state=Depends(state_dependency)) -> list[schemas.StormSummary]:
    return [_storm_summary(s) for s in state.list_storms()]


@router.get("/{storm_id}", response_model=schemas.StormDetail)
def get_storm(storm_id: str, state=Depends(state_dependency)) -> schemas.StormDetail:
    try:
        storm = state.get_storm(storm_id)
    except LookupError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    summary = _storm_summary(storm)
    return schemas.StormDetail(
        **summary.model_dump(),
        history=[
            schemas.FixOut(
                valid_time=f.valid_time,
                lat=f.lat,
                lon=f.lon,
                max_wind_kt=f.max_wind_kt,
                min_pressure_mb=f.min_pressure_mb,
                quality=f.quality.value,
            )
            for f in storm.track.fixes
        ],
        cycles=sorted(storm.cycles),
    )


@router.post(
    "/{storm_id}/cycles",
    response_model=schemas.CycleResult,
    status_code=status.HTTP_201_CREATED,
)
def run_cycle(
    storm_id: str, body: schemas.RunCycleRequest, state=Depends(state_dependency)
) -> schemas.CycleResult:
    coastline = (
        (body.coastline_lat, body.coastline_lon)
        if body.coastline_lat is not None and body.coastline_lon is not None
        else None
    )
    try:
        output = state.run_cycle(
            storm_id,
            body.cycle,
            lat=body.lat,
            lon=body.lon,
            wind_kt=body.wind_kt,
            members=body.members,
            worst_case=body.worst_case,
            coastline=coastline,
        )
    except LookupError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except CycleError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return convert.cycle_result_out(storm_id, output)


@router.get("/{storm_id}/cycles/{cycle}", response_model=schemas.CycleResult)
def get_cycle(storm_id: str, cycle: str, state=Depends(state_dependency)) -> schemas.CycleResult:
    try:
        output = state.get_cycle(storm_id, cycle)
    except LookupError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return convert.cycle_result_out(storm_id, output)
