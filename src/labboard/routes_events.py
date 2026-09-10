from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from .events import EventBroker, stream_events

router = APIRouter(tags=["events"])


@router.get("/events")
async def events(request: Request):
    broker: EventBroker = request.app.state.event_broker
    return StreamingResponse(
        stream_events(request, broker, request.headers.get("Last-Event-ID")),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
