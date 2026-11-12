import httpx
import pytest


def install_order_mocks(context, monkeypatch, *, cart):
    calls = []

    def fake_call(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if method == "GET" and url.endswith("/internal/cart/1"):
            return httpx.Response(200, json=cart)
        if method == "POST" and url.endswith("/reserve"):
            if url.endswith("/2/reserve") and cart.get("fail_second_reserve"):
                return httpx.Response(409, json={"detail": "Not enough stock"})
            return httpx.Response(200, json={})
        return httpx.Response(204)

    published = []
    monkeypatch.setattr(context.main, "call", fake_call)
    monkeypatch.setattr(
        context.main.events,
        "publish",
        lambda key, payload: published.append((key, payload)),
    )
    return calls, published


@pytest.mark.unit
def test_order_creation_uses_cart_reserves_stock_and_publishes_event(
    service_client_factory,
    monkeypatch,
):
    context = service_client_factory("order-service")
    cart = {
        "items": [
            {"product_id": 1, "name": "Lamp", "price": 25.0, "quantity": 2}
        ],
        "total": 50.0,
    }
    calls, published = install_order_mocks(context, monkeypatch, cart=cart)

    response = context.client.post(
        "/api/orders",
        headers={"X-User-ID": "1"},
    )

    assert response.status_code == 201
    assert response.json()["total"] == 50.0
    assert response.json()["status"] == "PENDING"
    assert [call[0] for call in calls] == ["GET", "POST", "DELETE"]
    assert [event[0] for event in published] == ["order.created"]
    with context.session_factory() as session:
        assert session.query(context.main.models.Order).count() == 1


@pytest.mark.unit
def test_empty_cart_cannot_create_order(service_client_factory, monkeypatch):
    context = service_client_factory("order-service")
    calls, published = install_order_mocks(
        context,
        monkeypatch,
        cart={"items": [], "total": 0.0},
    )

    response = context.client.post("/api/orders", headers={"X-User-ID": "1"})

    assert response.status_code == 400
    assert len(calls) == 1
    assert published == []
    with context.session_factory() as session:
        assert session.query(context.main.models.Order).count() == 0


@pytest.mark.unit
def test_failed_reservation_returns_conflict_and_releases_prior_items(
    service_client_factory,
    monkeypatch,
):
    context = service_client_factory("order-service")
    cart = {
        "items": [
            {"product_id": 1, "name": "Lamp", "price": 25.0, "quantity": 1},
            {"product_id": 2, "name": "Chair", "price": 40.0, "quantity": 1},
        ],
        "total": 65.0,
        "fail_second_reserve": True,
    }
    calls, published = install_order_mocks(context, monkeypatch, cart=cart)

    response = context.client.post("/api/orders", headers={"X-User-ID": "1"})

    assert response.status_code == 409
    assert any(url.endswith("/1/release") for _, url, _ in calls)
    assert published == []
    with context.session_factory() as session:
        assert session.query(context.main.models.Order).count() == 0


@pytest.mark.unit
def test_order_access_and_pending_order_cancellation(
    service_client_factory,
    monkeypatch,
):
    context = service_client_factory("order-service")
    model = context.main.models
    with context.session_factory() as session:
        pending = model.Order(
            user_id=1,
            total=25.0,
            status="PENDING",
            items=[
                model.OrderItem(
                    product_id=1,
                    name="Lamp",
                    price=25.0,
                    quantity=1,
                )
            ],
        )
        other_user = model.Order(user_id=2, total=10.0, status="PENDING", items=[])
        session.add_all([pending, other_user])
        session.commit()
        pending_id = pending.id
        other_id = other_user.id

    calls, published = install_order_mocks(
        context,
        monkeypatch,
        cart={"items": [], "total": 0.0},
    )
    own_order = context.client.get(
        f"/api/orders/{pending_id}",
        headers={"X-User-ID": "1", "X-User-Role": "user"},
    )
    forbidden = context.client.get(
        f"/api/orders/{other_id}",
        headers={"X-User-ID": "1", "X-User-Role": "user"},
    )
    missing = context.client.get(
        "/api/orders/999",
        headers={"X-User-ID": "1", "X-User-Role": "user"},
    )
    cancelled = context.client.post(
        f"/api/orders/{pending_id}/cancel",
        headers={"X-User-ID": "1", "X-User-Role": "user"},
    )

    assert own_order.status_code == 200
    assert forbidden.status_code == 403
    assert missing.status_code == 404
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"
    assert any(url.endswith("/1/release") for _, url, _ in calls)
    assert published[-1][0] == "order.cancelled"


@pytest.mark.unit
def test_cannot_cancel_order_that_is_not_pending(
    service_client_factory,
    monkeypatch,
):
    context = service_client_factory("order-service")
    model = context.main.models
    with context.session_factory() as session:
        paid = model.Order(user_id=1, total=25.0, status="PAID", items=[])
        session.add(paid)
        session.commit()
        order_id = paid.id
    install_order_mocks(context, monkeypatch, cart={"items": [], "total": 0.0})

    response = context.client.post(
        f"/api/orders/{order_id}/cancel",
        headers={"X-User-ID": "1"},
    )

    assert response.status_code == 409
