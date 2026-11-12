import json

import pytest


class StopConsumer(BaseException):
    pass


class FakeMethod:
    delivery_tag = 77
    routing_key = "order.created"


class FakeChannel:
    def __init__(self):
        self.callback = None
        self.acknowledgements = []
        self.rejections = []
        self.bindings = []
        self.message = None

    def exchange_declare(self, *args, **kwargs):
        pass

    def queue_declare(self, *args, **kwargs):
        pass

    def queue_bind(self, *args, **kwargs):
        self.bindings.append((args, kwargs))

    def basic_qos(self, *args, **kwargs):
        pass

    def basic_consume(self, queue, callback):
        self.callback = callback

    def basic_ack(self, delivery_tag):
        self.acknowledgements.append(delivery_tag)

    def basic_nack(self, delivery_tag, requeue):
        self.rejections.append((delivery_tag, requeue))

    def start_consuming(self):
        if self.message is not None:
            method, body = self.message
            self.callback(self, method, None, body)
        raise RuntimeError("stop after one callback")


class FakeConnection:
    is_open = True

    def __init__(self):
        self.channel_instance = FakeChannel()
        self.closed = False

    def channel(self):
        return self.channel_instance

    def close(self):
        self.closed = True
        self.is_open = False


def run_one_consumer_iteration(
    monkeypatch,
    events,
    body,
    *,
    handler,
    routing_key=None,
):
    connection = FakeConnection()
    monkeypatch.setattr(events.pika, "BlockingConnection", lambda _params: connection)

    class ImmediateThread:
        def __init__(self, target, daemon):
            self.target = target
            assert daemon is True

        def start(self):
            self.target()

    def stop_after_iteration(_seconds):
        raise StopConsumer()

    monkeypatch.setattr(events.threading, "Thread", ImmediateThread)
    monkeypatch.setattr(events.time, "sleep", stop_after_iteration)
    method = FakeMethod()
    if routing_key is not None:
        method.routing_key = routing_key
    connection.channel_instance.message = (method, body)
    with pytest.raises(StopConsumer):
        events.start_consumer(handler)
    return connection


@pytest.mark.unit
def test_payment_consumer_acknowledges_success_and_rejects_failed_processing(
    service_client_factory,
    monkeypatch,
):
    context = service_client_factory("payment-service")
    body = json.dumps({"order_id": 1}).encode()

    acknowledged = run_one_consumer_iteration(
        monkeypatch,
        context.main.events,
        body,
        handler=lambda _payload: None,
    )
    assert acknowledged.channel_instance.acknowledgements == [77]
    assert acknowledged.channel_instance.rejections == []

    def fail(_payload):
        raise ValueError("isolated handler failure")

    rejected = run_one_consumer_iteration(
        monkeypatch,
        context.main.events,
        body,
        handler=fail,
    )
    assert rejected.channel_instance.acknowledgements == []
    assert rejected.channel_instance.rejections == [(77, False)]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("body", "handler", "expected_requeue"),
    [
        (b"{broken", lambda _event_type, _payload: None, False),
        (
            json.dumps(["not", "an", "event"]).encode(),
            lambda _event_type, _payload: None,
            False,
        ),
        (
            json.dumps({"user_id": 1}).encode(),
            lambda _event_type, _payload: (_ for _ in ()).throw(
                RuntimeError("temporary storage failure")
            ),
            True,
        ),
    ],
)
def test_notification_consumer_ack_nack_and_retry_policy(
    service_client_factory,
    monkeypatch,
    body,
    handler,
    expected_requeue,
):
    context = service_client_factory("notification-service")

    connection = run_one_consumer_iteration(
        monkeypatch,
        context.main.events,
        body,
        handler=handler,
        routing_key="payment.completed",
    )
    channel = connection.channel_instance
    assert channel.acknowledgements == []
    assert channel.rejections == [(77, expected_requeue)]
    assert connection.closed is True


@pytest.mark.unit
def test_notification_consumer_acknowledges_valid_event(
    service_client_factory,
    monkeypatch,
):
    context = service_client_factory("notification-service")
    body = json.dumps({"user_id": 1, "order_id": 3}).encode()
    received = []
    connection = run_one_consumer_iteration(
        monkeypatch,
        context.main.events,
        body,
        handler=lambda event_type, payload: received.append((event_type, payload)),
        routing_key="payment.completed",
    )

    assert received == [("payment.completed", {"user_id": 1, "order_id": 3})]
    assert connection.channel_instance.acknowledgements == [77]
    assert connection.channel_instance.rejections == []
