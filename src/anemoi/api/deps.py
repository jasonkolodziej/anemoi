"""Shared FastAPI dependencies: demo state and the optional API key gate.

Auth is intentionally minimal for the reference implementation: a single
static header key, checked only when ``ANEMOI_API_KEY`` is set in the
environment. A real deployment replaces this with OAuth2/JWT -- see
docs/api.md ("Authentication and versioning").
"""

from __future__ import annotations

import os

from fastapi import Header, HTTPException, status

from .demo_state import DemoState, get_state

StateDep = DemoState


def state_dependency() -> DemoState:
    return get_state()


def require_api_key(x_anemoi_api_key: str | None = Header(default=None)) -> None:
    expected = os.environ.get("ANEMOI_API_KEY")
    if expected is None:
        return  # auth disabled for local/demo use
    if x_anemoi_api_key != expected:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or missing X-Anemoi-Api-Key")
