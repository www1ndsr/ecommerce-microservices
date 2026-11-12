from bson import ObjectId
import pytest

from tests.support.fakes import FakeMongoCollection


def notification_event(event_type="order.created", *, user_id=4, order_id=25):
    amount_field = "total" if event_type == "order.created" else "amount"
    return {
        "user_id": user_id,
        "order_id": order_id,
        amount_field: 50.0,
        "reason": "",
    }


def attach_fake_mongo(context, monkeypatch):
    notifications = FakeMongoCollection()
    processed_events = FakeMongoCollection()
    monkeypatch.setattr(
        context.main.db,
        "notifications",
        notifications,
    )
    monkeypatch.setattr(
        context.main.db,
        "processed_events",
        processed_events,
    )
    return notifications, processed_events


@pytest.mark.unit
@pytest.mark.parametrize(
    ("event_type", "expected_title"),
    [
        ("order.created", "Заказ создан"),
        ("payment.completed", "Оплата прошла"),
        ("payment.failed", "Оплата не прошла"),
    ],
)
def test_supported_events_build_notifications(event_type, expected_title):
    from tests.support.service_loader import load_service

    main = load_service("notification-service")

    result = main.models.from_event(event_type, notification_event(event_type))

    assert result["event_key"] == f"{event_type}:25"
    assert result["title"] == expected_title
    assert result["user_id"] == 4
    assert result["is_read"] is False


@pytest.mark.unit
@pytest.mark.parametrize(
    ("event_type", "payload"),
    [
        ("unknown.event", notification_event()),
        ("order.created", notification_event(user_id=0)),
        ("order.created", notification_event(order_id=-1)),
        ("order.created", {"user_id": 4, "order_id": 25, "total": float("nan")}),
        (
            "payment.failed",
            {
                **notification_event("payment.failed"),
                "reason": 12,
            },
        ),
    ],
)
def test_invalid_notification_events_are_rejected(event_type, payload):
    from tests.support.service_loader import load_service

    main = load_service("notification-service")

    with pytest.raises(main.models.InvalidEventError):
        main.models.from_event(event_type, payload)


@pytest.mark.unit
def test_notification_event_handler_is_idempotent(
    service_client_factory,
    monkeypatch,
):
    context = service_client_factory("notification-service")
    notifications, _ = attach_fake_mongo(context, monkeypatch)
    event = notification_event()

    context.main.handle_event("order.created", event)
    context.main.handle_event("order.created", event)

    assert len(notifications.documents) == 1
    document = next(iter(notifications.documents.values()))
    assert document["event_key"] == "order.created:25"


@pytest.mark.unit
def test_notification_api_lists_marks_read_and_deletes_own_record(
    service_client_factory,
    monkeypatch,
):
    context = service_client_factory("notification-service")
    notifications, _ = attach_fake_mongo(context, monkeypatch)
    context.main.handle_event("order.created", notification_event())
    document = next(iter(notifications.documents.values()))
    notification_id = str(document["_id"])
    headers = {"X-User-ID": "4"}

    listed = context.client.get("/api/notifications", headers=headers)
    unread = context.client.get("/api/notifications/unread", headers=headers)
    marked_read = context.client.patch(
        f"/api/notifications/{notification_id}/read",
        headers=headers,
    )
    unread_after = context.client.get("/api/notifications/unread", headers=headers)
    deleted = context.client.delete(
        f"/api/notifications/{notification_id}",
        headers=headers,
    )

    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert unread.status_code == 200
    assert len(unread.json()) == 1
    assert marked_read.status_code == 200
    assert marked_read.json()["is_read"] is True
    assert unread_after.status_code == 200
    assert unread_after.json() == []
    assert deleted.status_code == 204


@pytest.mark.unit
def test_notification_access_is_limited_to_own_identity(
    service_client_factory,
    monkeypatch,
):
    context = service_client_factory("notification-service")
    notifications, _ = attach_fake_mongo(context, monkeypatch)
    context.main.handle_event("order.created", notification_event())
    notification_id = str(next(iter(notifications.documents.values()))["_id"])

    unauthenticated = context.client.get("/api/notifications")
    other_user = context.client.patch(
        f"/api/notifications/{notification_id}/read",
        headers={"X-User-ID": "8"},
    )
    malformed_id = context.client.delete(
        "/api/notifications/not-an-object-id",
        headers={"X-User-ID": "4"},
    )

    assert unauthenticated.status_code == 401
    assert other_user.status_code == 404
    assert malformed_id.status_code == 404
