"""WebSocket push of cycle completions.

Reference implementation only: it polls :class:`DemoState` in-process and
pushes new cycle results as they appear. A real deployment replaces the
polling loop with a subscription to whatever publishes ``CycleOutput``
(a queue, MLflow webhook, etc.) -- the wire message shape is what matters
here, not the polling.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from . import convert
from .deps import get_state

router = APIRouter(tags=["stream"])

POLL_INTERVAL_SECONDS = 2.0


@router.websocket("/storms/{storm_id}/stream")
async def storm_stream(websocket: WebSocket, storm_id: str) -> None:
    """Pushes ``{"type": "cycle", "data": <CycleResult>}`` for every cycle
    already on record, then for each new one as it is run, until the client
    disconnects. Sends ``{"type": "error", "detail": ...}`` and closes if the
    storm does not exist.
    """
    await websocket.accept()
    state = get_state()
    try:
        storm = state.get_storm(storm_id)
    except LookupError as exc:
        await websocket.send_json({"type": "error", "detail": str(exc)})
        await websocket.close()
        return

    sent: set[str] = set()
    try:
        while True:
            for label in sorted(storm.cycles):
                if label not in sent:
                    result = convert.cycle_result_out(storm_id, storm.cycles[label])
                    await websocket.send_json({"type": "cycle", "data": result.model_dump(mode="json")})
                    sent.add(label)
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
    except WebSocketDisconnect:
        return
