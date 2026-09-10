from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator


@dataclass(frozen=True)
class Event:
    event_id: int
    event: str
    data: dict[str, object]

    def encode(self) -> str:
        return f"id: {self.event_id}\nevent: {self.event}\ndata: {json.dumps(self.data)}\n\n"


class EventBroker:
    def __init__(self, queue_size: int = 32) -> None:
        self.queue_size = queue_size
        self._next_id = 0
        self._subscribers: set[asyncio.Queue[Event]] = set()

    @property
    def current_id(self) -> int:
        return self._next_id

    def subscribe(self) -> asyncio.Queue[Event]:
        queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=self.queue_size)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[Event]) -> None:
        self._subscribers.discard(queue)

    async def publish(self, event: str, data: dict[str, object] | None = None) -> Event:
        self._next_id += 1
        item = Event(self._next_id, event, data or {})
        for queue in tuple(self._subscribers):
            try:
                queue.put_nowait(item)
            except asyncio.QueueFull:
                self._subscribers.discard(queue)
        return item

    @asynccontextmanager
    async def connected(self) -> AsyncIterator[asyncio.Queue[Event]]:
        queue = self.subscribe()
        try:
            yield queue
        finally:
            self.unsubscribe(queue)


async def stream_events(request, broker: EventBroker, last_event_id: str | None) -> AsyncIterator[str]:
    try:
        parsed_last_id = int(last_event_id) if last_event_id else 0
    except ValueError:
        parsed_last_id = 0
    async with broker.connected() as queue:
        yield f"retry: 5000\n\n"
        yield Event(
            broker.current_id,
            "refetch",
            {"reason": "reconnect" if parsed_last_id else "initial"},
        ).encode()
        while True:
            if await request.is_disconnected():
                break
            try:
                item = await asyncio.wait_for(queue.get(), timeout=20)
            except asyncio.TimeoutError:
                yield ": heartbeat\n\n"
                continue
            yield item.encode()
