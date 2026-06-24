from __future__ import annotations

import asyncio

import pytest

from kie_sidecar.services.event_bus import EventBus, SidecarEvent


@pytest.mark.asyncio
async def test_event_bus_broadcast_reaches_subscriber():
    bus = EventBus()
    queue = bus.subscribe()

    await bus.broadcast("session.usage", {"spent": 10, "limit": 100})
    event = await asyncio.wait_for(queue.get(), timeout=1)
    assert event == SidecarEvent("session.usage", {"spent": 10, "limit": 100})
    bus.unsubscribe(queue)


@pytest.mark.asyncio
async def test_app_state_event_bus_broadcast(client):
    state = client.app.state.app_state
    queue = state.event_bus.subscribe()
    try:
        await state.event_bus.broadcast(
            "generation.updated",
            {"id": "test-gen", "status": "running", "type": "image"},
        )
        event = await asyncio.wait_for(queue.get(), timeout=1)
        assert event.event_type == "generation.updated"
        assert event.data["id"] == "test-gen"
    finally:
        state.event_bus.unsubscribe(queue)


def test_events_route_registered(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json().get("paths", {})
    assert "/api/v1/events" in paths
