import pytest


def insert_product(context, *, name="Desk Lamp", stock=5, price=24.5):
    with context.session_factory() as session:
        product = context.main.models.Product(
            name=name,
            description="Test product",
            price=price,
            stock=stock,
            image_url="",
        )
        session.add(product)
        session.commit()
        session.refresh(product)
        return product.id


@pytest.mark.unit
def test_product_list_search_and_details(service_client_factory):
    context = service_client_factory("product-service")
    product_id = insert_product(context)
    insert_product(context, name="Desk Chair")

    listing = context.client.get("/api/products", params={"q": "Lamp", "limit": 1})
    details = context.client.get(f"/api/products/{product_id}")
    missing = context.client.get("/api/products/999")

    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["name"] == "Desk Lamp"
    assert details.status_code == 200
    assert details.json()["id"] == product_id
    assert missing.status_code == 404


@pytest.mark.unit
def test_product_changes_require_admin_and_validate_fields(
    service_client_factory,
):
    context = service_client_factory("product-service")
    payload = {
        "name": "Desk Lamp",
        "description": "Test product",
        "price": 24.5,
        "stock": 5,
        "image_url": "",
    }

    forbidden = context.client.post("/api/products", json=payload)
    invalid = context.client.post(
        "/api/products",
        headers={"X-User-Role": "admin"},
        json={**payload, "price": 0},
    )
    created = context.client.post(
        "/api/products",
        headers={"X-User-Role": "admin"},
        json=payload,
    )

    assert forbidden.status_code == 403
    assert invalid.status_code == 422
    assert created.status_code == 201
    product_id = created.json()["id"]

    changed = context.client.put(
        f"/api/products/{product_id}",
        headers={"X-User-Role": "admin"},
        json={**payload, "name": "Updated Lamp"},
    )
    deleted = context.client.delete(
        f"/api/products/{product_id}",
        headers={"X-User-Role": "admin"},
    )

    assert changed.status_code == 200
    assert changed.json()["name"] == "Updated Lamp"
    assert deleted.status_code == 204


@pytest.mark.unit
def test_stock_reservation_is_owned_by_inventory_service(service_client_factory):
    context = service_client_factory("product-service")
    product_id = insert_product(context, stock=3)

    response = context.client.post(
        f"/internal/products/{product_id}/reserve",
        json={"quantity": 2},
    )

    assert response.status_code == 404
