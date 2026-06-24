from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SidecarEvent:
    event_type: str
    data: dict[str, Any]


@dataclass
class EventBus:
    _subscribers: list[asyncio.Queue[SidecarEvent]] = field(default_factory=list)

    def subscribe(self) -> asyncio.Queue[SidecarEvent]:
        queue: asyncio.Queue[SidecarEvent] = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[SidecarEvent]) -> None:
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    async def broadcast(self, event_type: str, data: dict[str, Any]) -> None:
        event = SidecarEvent(event_type=event_type, data=data)
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                self.unsubscribe(queue)
