import pytest


def payment_event(order_id, total):
    return {
        "order_id": order_id,
        "user_id": 4,
        "total": total,
        "request_id": "unit-test-request",
    }


@pytest.mark.unit
def test_order_event_creates_completed_payment_once(
    service_client_factory,
    monkeypatch,
):
    context = service_client_factory("payment-service")
    published = []
    monkeypatch.setattr(
        context.main.events,
        "publish",
        lambda key, payload: published.append((key, payload)),
    )

    context.main.handle_order_created(payment_event(20, 125.0))
    context.main.handle_order_created(payment_event(20, 125.0))

    with context.session_factory() as session:
        payments = session.query(context.main.models.Payment).all()
        assert len(payments) == 1
        assert payments[0].status == "COMPLETED"
    assert [key for key, _ in published] == ["payment.completed"]


@pytest.mark.unit
def test_amount_above_configured_maximum_fails_payment(
    service_client_factory,
    monkeypatch,
):
    context = service_client_factory("payment-service")
    published = []
    monkeypatch.setattr(
        context.main.events,
        "publish",
        lambda key, payload: published.append((key, payload)),
    )
    amount = context.main.settings.max_amount + 0.01

    context.main.handle_order_created(payment_event(21, amount))

    with context.session_factory() as session:
        payment = session.query(context.main.models.Payment).one()
        assert payment.status == "FAILED"
        assert payment.amount == amount
    assert [key for key, _ in published] == ["payment.failed"]


@pytest.mark.unit
def test_payment_status_endpoint_enforces_identity_and_ownership(
    service_client_factory,
):
    context = service_client_factory("payment-service")
    with context.session_factory() as session:
        payment = context.main.models.Payment(
            order_id=25,
            user_id=4,
            amount=40.0,
            status="COMPLETED",
            reason="",
        )
        session.add(payment)
        session.commit()

    missing_identity = context.client.get("/api/payments/order/25")
    forbidden = context.client.get(
        "/api/payments/order/25",
        headers={"X-User-ID": "8", "X-User-Role": "user"},
    )
    owner = context.client.get(
        "/api/payments/order/25",
        headers={"X-User-ID": "4", "X-User-Role": "user"},
    )
    missing_payment = context.client.get(
        "/api/payments/order/999",
        headers={"X-User-ID": "4", "X-User-Role": "user"},
    )

    assert missing_identity.status_code == 401
    assert forbidden.status_code == 403
    assert owner.status_code == 200
    assert owner.json()["status"] == "COMPLETED"
    assert missing_payment.status_code == 404
