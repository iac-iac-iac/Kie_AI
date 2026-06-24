from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/events", tags=["events"])

PING_INTERVAL_SEC = 30


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _sse_ping() -> str:
    return ": ping\n\n"


async def _event_stream(request: Request) -> AsyncIterator[str]:
    state = request.app.state.app_state
    queue = state.event_bus.subscribe()
    try:
        while True:
            if await request.is_disconnected():
                break
            try:
                event = await asyncio.wait_for(queue.get(), timeout=PING_INTERVAL_SEC)
                yield _sse_event(event.event_type, event.data)
            except asyncio.TimeoutError:
                yield _sse_ping()
    finally:
        state.event_bus.unsubscribe(queue)


@router.get("")
async def stream_events(request: Request) -> StreamingResponse:
    return StreamingResponse(
        _event_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
