import pytest


@pytest.mark.asyncio
async def test_broker_bounded_disconnect():
    from labboard.events import EventBroker

    broker = EventBroker(queue_size=1)
    queue = broker.subscribe()
    await broker.publish("announcement", {"id": 1})
    await broker.publish("announcement", {"id": 2})
    assert queue not in broker._subscribers


@pytest.mark.asyncio
async def test_stream_starts_with_refetch():
    from labboard.events import EventBroker, stream_events

    class Request:
        async def is_disconnected(self):
            return False

    stream = stream_events(Request(), EventBroker(), None)
    assert "retry: 5000" in await anext(stream)
    assert "event: refetch" in await anext(stream)
    await stream.aclose()
