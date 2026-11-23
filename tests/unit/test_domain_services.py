import pytest
import httpx


@pytest.mark.unit
@pytest.mark.parametrize(
    "service_name",
    [
        "inventory-service",
        "review-service",
        "promotion-service",
        "shipping-service",
        "wishlist-service",
    ],
)
def test_new_services_expose_health_and_database_readiness(
    service_client_factory, service_name
):
    context = service_client_factory(service_name)

    assert context.client.get("/health").json() == {"status": "ok"}
    assert context.client.get("/ready").json() == {"status": "ready"}


@pytest.mark.unit
def test_inventory_owns_reservations_and_compensating_release(
    service_client_factory,
):
    context = service_client_factory("inventory-service")
    headers = {"X-User-Role": "admin"}

    empty = context.client.put("/api/inventory/8", headers=headers, json={"quantity": 0})
    configured = context.client.put(
        "/api/inventory/7", headers=headers, json={"quantity": 4}
    )
    reserved = context.client.post(
        "/internal/inventory/7/reserve", json={"quantity": 3}
    )
    conflict = context.client.post(
        "/internal/inventory/7/reserve", json={"quantity": 2}
    )
    released = context.client.post(
        "/internal/inventory/7/release", json={"quantity": 1}
    )

    assert configured.status_code == 200
    assert empty.json()["available"] == 0
    assert reserved.json() == {"product_id": 7, "available": 1, "reserved": 3}
    assert conflict.status_code == 409
    assert released.json() == {"product_id": 7, "available": 2, "reserved": 2}


@pytest.mark.unit
def test_inventory_admin_and_batch_availability_endpoints(service_client_factory):
    context = service_client_factory("inventory-service")
    forbidden = context.client.put("/api/inventory/9", json={"quantity": 6})
    context.client.put(
        "/api/inventory/9",
        headers={"X-User-Role": "admin"},
        json={"quantity": 6},
    )
    listed = context.client.get("/api/inventory?product_ids=9,99")

    assert forbidden.status_code == 403
    assert listed.json() == [
        {"product_id": 9, "available": 6, "reserved": 0},
        {"product_id": 99, "available": 0, "reserved": 0},
    ]


@pytest.mark.unit
def test_reviews_are_scoped_to_the_author_for_deletion(service_client_factory):
    context = service_client_factory("review-service")
    created = context.client.post(
        "/api/reviews",
        headers={"X-User-ID": "12"},
        json={"product_id": 3, "rating": 5, "comment": "Отлично"},
    )
    review_id = created.json()["id"]
    duplicate = context.client.post(
        "/api/reviews",
        headers={"X-User-ID": "12"},
        json={"product_id": 3, "rating": 4, "comment": "Повтор"},
    )
    other_user = context.client.delete(
        f"/api/reviews/{review_id}", headers={"X-User-ID": "13"}
    )
    listed = context.client.get("/api/reviews?product_id=3")
    summary = context.client.get("/api/reviews/summary/3")
    owner = context.client.delete(
        f"/api/reviews/{review_id}", headers={"X-User-ID": "12"}
    )

    assert created.status_code == 201
    assert duplicate.status_code == 409
    assert other_user.status_code == 403
    assert len(listed.json()) == 1
    assert summary.json() == {"product_id": 3, "average_rating": 5.0, "review_count": 1}
    assert owner.status_code == 204


@pytest.mark.unit
def test_promotion_requires_admin_and_normalizes_code(service_client_factory):
    context = service_client_factory("promotion-service")
    forbidden = context.client.post(
        "/api/promotions", json={"code": "save10", "discount_percent": 10}
    )
    created = context.client.post(
        "/api/promotions",
        headers={"X-User-Role": "admin"},
        json={"code": "save10", "discount_percent": 10},
    )
    duplicate = context.client.post(
        "/api/promotions",
        headers={"X-User-Role": "admin"},
        json={"code": "SAVE10", "discount_percent": 10},
    )
    found = context.client.get("/api/promotions/save10")
    quote = context.client.post(
        "/api/promotions/validate",
        json={"code": "save10", "subtotal": 100},
    )
    deactivated = context.client.patch(
        "/api/promotions/SAVE10",
        headers={"X-User-Role": "admin"},
        json={"active": False},
    )
    inactive = context.client.get("/api/promotions/SAVE10")

    assert forbidden.status_code == 403
    assert created.json()["code"] == "SAVE10"
    assert duplicate.status_code == 409
    assert found.json()["discount_percent"] == 10
    assert quote.json()["total"] == 90
    assert deactivated.status_code == 200
    assert inactive.status_code == 404


@pytest.mark.unit
def test_shipping_access_control_and_status_updates(
    service_client_factory, monkeypatch
):
    context = service_client_factory("shipping-service")
    upstream_calls = []

    def paid_order(url, *, headers, timeout):
        upstream_calls.append((url, headers, timeout))
        request = httpx.Request("GET", url, headers=headers)
        return httpx.Response(
            200, json={"status": "PAID", "user_id": 12}, request=request
        )

    monkeypatch.setattr(context.main.httpx, "get", paid_order)
    created = context.client.post(
        "/api/shipping",
        headers={"X-User-ID": "1", "X-User-Role": "admin"},
        json={"order_id": 44, "address": "Main street 10"},
    )
    forbidden = context.client.get(
        "/api/shipping/44",
        headers={"X-User-ID": "13", "X-User-Role": "user"},
    )
    processing = context.client.patch(
        "/api/shipping/44/status",
        headers={"X-User-Role": "admin"},
        json={"status": "PROCESSING"},
    )
    updated = context.client.patch(
        "/api/shipping/44/status",
        headers={"X-User-Role": "admin"},
        json={"status": "SHIPPED"},
    )
    duplicate = context.client.post(
        "/api/shipping",
        headers={"X-User-ID": "12"},
        json={"order_id": 44, "address": "Main street 10"},
    )

    assert created.status_code == 201
    assert upstream_calls[0][1]["X-User-ID"] == "1"
    assert context.client.get(
        "/api/shipping/44", headers={"X-User-ID": "12"}
    ).status_code == 200
    assert forbidden.status_code == 403
    assert processing.status_code == 200
    assert updated.json()["status"] == "SHIPPED"
    assert duplicate.status_code == 409


@pytest.mark.unit
def test_shipping_requires_a_paid_order(service_client_factory, monkeypatch):
    context = service_client_factory("shipping-service")
    request = httpx.Request("GET", "http://order-service/api/orders/44")
    monkeypatch.setattr(
        context.main.httpx,
        "get",
        lambda *args, **kwargs: httpx.Response(
            200, json={"status": "PENDING"}, request=request
        ),
    )

    response = context.client.post(
        "/api/shipping",
        headers={"X-User-ID": "12"},
        json={"order_id": 44, "address": "Main street 10"},
    )

    assert response.status_code == 409
    assert context.client.get(
        "/api/shipping/44", headers={"X-User-ID": "12"}
    ).status_code == 404


@pytest.mark.unit
def test_wishlist_is_user_scoped_and_duplicate_add_is_idempotent(
    service_client_factory,
):
    context = service_client_factory("wishlist-service")
    headers = {"X-User-ID": "12"}
    first = context.client.post(
        "/api/wishlist", headers=headers, json={"product_id": 3}
    )
    second = context.client.post(
        "/api/wishlist", headers=headers, json={"product_id": 3}
    )
    other_user = context.client.get(
        "/api/wishlist", headers={"X-User-ID": "13"}
    )
    removed = context.client.delete("/api/wishlist/3", headers=headers)
    context.client.post("/api/wishlist", headers=headers, json={"product_id": 4})
    cleared = context.client.delete("/api/wishlist", headers=headers)
    unauthenticated = context.client.get("/api/wishlist")

    assert first.status_code == second.status_code == 201
    assert other_user.json() == []
    assert removed.status_code == 204
    assert cleared.status_code == 204
    assert context.client.get("/api/wishlist", headers=headers).json() == []
    assert unauthenticated.status_code == 401
