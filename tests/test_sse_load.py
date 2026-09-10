import pytest

from labboard.events import EventBroker


@pytest.mark.asyncio
async def test_150_subscribers_receive_bounded_event():
    broker = EventBroker(queue_size=4)
    queues = [broker.subscribe() for _ in range(150)]
    await broker.publish("announcement", {"action": "published", "id": 1})
    events = [queue.get_nowait() for queue in queues]
    assert len(events) == 150
    assert {event.event_id for event in events} == {1}
    for queue in queues:
        broker.unsubscribe(queue)
