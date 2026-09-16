"""Retraining triggers (§5.5, §5.7).

Read-only in v1: this reports what ``anemoi.training.triggers.evaluate_all``
would schedule right now, given the demo's drift/skew/season state. Actually
launching a training job is out of scope for the reference API -- see
docs/api.md ("The one mutating route") for why that stays a queue/orchestrator
concern rather than a synchronous POST.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import convert, schemas
from ..deps import require_api_key, state_dependency

router = APIRouter(prefix="/retraining", tags=["retraining"], dependencies=[Depends(require_api_key)])


@router.get("/triggers", response_model=list[schemas.RetrainJobOut])
def pending_triggers(state=Depends(state_dependency)) -> list[schemas.RetrainJobOut]:
    jobs = state.pending_retrain_jobs()
    return [convert.retrain_job_out(j) for j in jobs]
