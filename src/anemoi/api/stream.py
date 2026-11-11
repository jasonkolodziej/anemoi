"""WebSocket push of cycle completions.

Reference implementation only: it polls the API's state (`deps.
state_dependency`, so the real state in a real deployment -- it read the demo
state unconditionally before #212, and so answered "unknown storm" for every
real one) and pushes new cycle results as they appear. A real deployment replaces the
polling loop with a subscription to whatever publishes ``CycleOutput``
(a queue, MLflow webhook, etc.) -- the wire message shape is what matters
here, not the polling.
"""

from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from . import convert
from .deps import require_api_key, state_dependency

router = APIRouter(tags=["stream"], dependencies=[Depends(require_api_key)])

POLL_INTERVAL_SECONDS = 2.0
#: An open socket is an in-flight request, which keeps the real container
#: from ever sleeping (`sleepAfter`); a client that wants more reconnects.
MAX_STREAM_SECONDS = 15 * 60


@router.websocket("/storms/{storm_id}/stream")
async def storm_stream(websocket: WebSocket, storm_id: str) -> None:
    """Pushes ``{"type": "cycle", "data": <CycleResult>}`` for every cycle
    already on record, then for each new one as it is run, until the client
    disconnects. Sends ``{"type": "error", "detail": ...}`` and closes if the
    storm does not exist.
    """
    await websocket.accept()
    state = state_dependency()
    try:
        # Off the event loop: the real state may fetch the live feed first.
        storm = await asyncio.to_thread(state.get_storm, storm_id)
    except LookupError as exc:
        await websocket.send_json({"type": "error", "detail": str(exc)})
        await websocket.close()
        return

    sent: set[str] = set()
    deadline = time.monotonic() + MAX_STREAM_SECONDS
    try:
        while time.monotonic() < deadline:
            for label in sorted(storm.cycles):
                if label in sent:
                    continue
                try:
                    # A stored real cycle is downloaded on first read.
                    stored = await asyncio.to_thread(storm.cycles.__getitem__, label)
                except KeyError:
                    continue  # unreadable right now; tried again next poll
                result = convert.cycle_result_out(storm_id, stored)
                await websocket.send_json({"type": "cycle", "data": result.model_dump(mode="json")})
                sent.add(label)
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
        await websocket.close()
    except WebSocketDisconnect:
        return
