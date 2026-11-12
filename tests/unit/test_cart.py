import pytest
import redis
from fastapi import HTTPException

from tests.support.fakes import FakeRedis


def setup_cart(context, monkeypatch, *, product=None):
    monkeypatch.setattr(context.main, "r", FakeRedis())
    available_product = product or {
        "id": 3,
        "name": "Desk Lamp",
        "price": 24.5,
        "stock": 5,
    }

    def fetch_product(product_id):
        if product_id != available_product["id"]:
            raise HTTPException(404, "Product not found")
        return available_product

    monkeypatch.setattr(context.main, "fetch_product", fetch_product)


@pytest.mark.unit
def test_cart_add_get_remove_and_empty_state(
    service_client_factory,
    monkeypatch,
):
    context = service_client_factory("cart-service")
    setup_cart(context, monkeypatch)
    headers = {"X-User-ID": "12"}

    empty = context.client.get("/api/cart", headers=headers)
    added = context.client.post(
        "/api/cart/items",
        headers=headers,
        json={"product_id": 3, "quantity": 2},
    )
    removed = context.client.delete("/api/cart/items/3", headers=headers)
    empty_again = context.client.get("/api/cart", headers=headers)

    assert empty.status_code == 200
    assert empty.json() == {"items": [], "total": 0}
    assert added.status_code == 200
    assert added.json()["total"] == 49.0
    assert added.json()["items"][0]["quantity"] == 2
    assert removed.status_code == 200
    assert removed.json() == {"items": [], "total": 0}
    assert empty_again.status_code == 200


@pytest.mark.unit
def test_cart_rejects_unknown_product_and_quantity_outside_schema(
    service_client_factory,
    monkeypatch,
):
    context = service_client_factory("cart-service")
    setup_cart(context, monkeypatch)
    headers = {"X-User-ID": "12"}

    unknown = context.client.post(
        "/api/cart/items",
        headers=headers,
        json={"product_id": 999, "quantity": 1},
    )
    invalid_quantity = context.client.post(
        "/api/cart/items",
        headers=headers,
        json={"product_id": 3, "quantity": 100},
    )

    assert unknown.status_code == 404
    assert invalid_quantity.status_code == 422


@pytest.mark.unit
def test_cart_enforces_stock_and_returns_service_unavailable_on_redis_error(
    service_client_factory,
    monkeypatch,
):
    context = service_client_factory("cart-service")
    setup_cart(
        context,
        monkeypatch,
        product={"id": 3, "name": "Desk Lamp", "price": 24.5, "stock": 1},
    )
    headers = {"X-User-ID": "12"}
    over_stock = context.client.post(
        "/api/cart/items",
        headers=headers,
        json={"product_id": 3, "quantity": 2},
    )

    def fail_read(_name):
        raise redis.RedisError("isolated test failure")

    monkeypatch.setattr(context.main.r, "hgetall", fail_read)
    storage_error = context.client.get("/api/cart", headers=headers)

    assert over_stock.status_code == 409
    assert storage_error.status_code == 503


@pytest.mark.unit
def test_cart_clear_requires_identity_and_returns_no_content(
    service_client_factory,
    monkeypatch,
):
    context = service_client_factory("cart-service")
    setup_cart(context, monkeypatch)

    unauthenticated = context.client.get("/api/cart")
    cleared = context.client.delete("/api/cart", headers={"X-User-ID": "12"})

    assert unauthenticated.status_code == 401
    assert cleared.status_code == 204
