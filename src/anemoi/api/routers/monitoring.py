"""Train/serve drift and skew monitoring (§4.6.3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ...data.sources import Flavor
from ...tracking.registry import ALL_MODELS
from .. import convert, schemas
from ..deps import require_api_key, state_dependency

router = APIRouter(prefix="/monitoring", tags=["monitoring"], dependencies=[Depends(require_api_key)])


@router.get("/drift/{model}", response_model=schemas.DriftReportOut)
def drift(model: str, state=Depends(state_dependency)) -> schemas.DriftReportOut:
    if model not in ALL_MODELS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown model {model!r}; expected one of {ALL_MODELS}")
    report = state.drift_report(model)
    return convert.drift_report_out(model, Flavor.GDAS_FINETUNE.value, report)


@router.get("/drift", response_model=list[schemas.DriftReportOut])
def drift_all(state=Depends(state_dependency)) -> list[schemas.DriftReportOut]:
    """Drift across every tracked model in one call -- what a monitoring
    dashboard's landing view wants, instead of six round trips."""
    return [
        convert.drift_report_out(m, Flavor.GDAS_FINETUNE.value, state.drift_report(m))
        for m in ALL_MODELS
    ]


@router.get("/skew", response_model=schemas.SkewReportOut)
def skew(
    lead_hours: int = Query(48, description="Forecast lead time the audit is run at"),
    state=Depends(state_dependency),
) -> schemas.SkewReportOut:
    """ERA5T-vs-operational paired audit (§4.6.3). Real deployments run this
    ~5 days after each cycle, once ERA5T is available; the demo returns a
    synthetic sample on every call."""
    return convert.skew_report_out(state.skew_report(lead_hours=lead_hours))
