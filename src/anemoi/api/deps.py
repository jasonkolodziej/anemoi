"""Shared FastAPI dependencies: demo/real state and the optional API key gate.

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
    """``DemoState`` (synthetic, always available) by default; opt into
    `real_state.RealState` (real HURDAT2 storms, real trained models via
    #78/#85's real inference wiring) by setting ``ANEMOI_API_REAL_STATE``
    -- every router already depends on this dependency's return value
    only through the shared list_storms/get_storm/run_cycle/get_cycle
    surface, per `routers.storms`'s own docstring, so no route changes
    when this switches."""
    if os.environ.get("ANEMOI_API_REAL_STATE"):
        from .real_state import get_real_state

        return get_real_state()
    return get_state()


def require_api_key(x_anemoi_api_key: str | None = Header(default=None)) -> None:
    expected = os.environ.get("ANEMOI_API_KEY")
    if expected is None:
        return  # auth disabled for local/demo use
    if x_anemoi_api_key != expected:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or missing X-Anemoi-Api-Key")
