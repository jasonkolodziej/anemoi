"""Operator-only maintenance routes, called by the anemoi-api-real Worker
(docker/api/src/index.ts) rather than by API clients. The Worker's public
`fetch` handler 404s every `/v1/internal/*` path, so only its own cron
reaches these, through the container binding directly. Hidden from the
OpenAPI schema for the same reason.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import require_api_key, state_dependency

router = APIRouter(
    prefix="/internal", include_in_schema=False, dependencies=[Depends(require_api_key)],
)


@router.post("/calibration-audit")
def calibration_audit(state=Depends(state_dependency)) -> dict:
    """Audit every live storm's stored cycles against its newest fixes.
    `DemoState` has no stored cycles to audit, so it reports zero."""
    run = getattr(state, "run_calibration_audit", None)
    return {"new_samples": run() if run is not None else 0}
