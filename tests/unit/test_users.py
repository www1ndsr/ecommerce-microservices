import pytest


@pytest.mark.unit
def test_profile_is_created_and_can_be_updated(service_client_factory):
    context = service_client_factory("user-service")
    headers = {"X-User-ID": "7"}

    initial = context.client.get("/api/users/me", headers=headers)
    updated = context.client.put(
        "/api/users/me",
        headers=headers,
        json={
            "full_name": "Test Buyer",
            "phone": "+1 (555) 010-2000",
            "address": "Test Street 10",
        },
    )

    assert initial.status_code == 200
    assert initial.json() == {
        "user_id": 7,
        "full_name": "",
        "phone": "",
        "address": "",
    }
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Test Buyer"
    assert updated.json()["phone"] == "+1 (555) 010-2000"
    with context.session_factory() as session:
        assert session.query(context.main.models.Profile).count() == 1


@pytest.mark.unit
def test_profile_requires_gateway_identity_header(service_client_factory):
    context = service_client_factory("user-service")

    response = context.client.get("/api/users/me")

    assert response.status_code == 401


@pytest.mark.unit
def test_profile_validation_and_user_ownership(service_client_factory):
    context = service_client_factory("user-service")
    with context.session_factory() as session:
        session.add(
            context.main.models.Profile(
                user_id=8,
                full_name="Other Buyer",
                phone="",
                address="",
            )
        )
        session.commit()

    invalid_profile = context.client.put(
        "/api/users/me",
        headers={"X-User-ID": "7"},
        json={"full_name": "Buyer", "phone": "not-a-phone", "address": ""},
    )
    forbidden = context.client.get(
        "/api/users/8",
        headers={"X-User-ID": "7", "X-User-Role": "user"},
    )
    admin_access = context.client.get(
        "/api/users/8",
        headers={"X-User-ID": "7", "X-User-Role": "admin"},
    )
    missing = context.client.get(
        "/api/users/99",
        headers={"X-User-ID": "7", "X-User-Role": "admin"},
    )

    assert invalid_profile.status_code == 422
    assert forbidden.status_code == 403
    assert admin_access.status_code == 200
    assert admin_access.json()["user_id"] == 8
    assert missing.status_code == 404
