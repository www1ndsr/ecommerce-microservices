from datetime import datetime, timedelta, timezone

import jwt
import pytest


@pytest.mark.unit
def test_registration_normalizes_email_and_returns_verifiable_jwt(
    service_client_factory,
):
    context = service_client_factory("auth-service")

    response = context.client.post(
        "/api/auth/register",
        json={"email": "Buyer@Example.com", "password": "valid-password"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    claims = jwt.decode(
        body["access_token"],
        "unit-test-only-secret",
        algorithms=["HS256"],
    )
    assert claims["sub"] == "1"
    assert claims["role"] == "user"
    with context.session_factory() as session:
        account = session.query(context.main.models.Account).one()
        assert account.email == "buyer@example.com"


@pytest.mark.unit
def test_duplicate_registration_returns_conflict(service_client_factory):
    context = service_client_factory("auth-service")
    credentials = {"email": "buyer@example.com", "password": "valid-password"}

    assert context.client.post("/api/auth/register", json=credentials).status_code == 201
    duplicate = context.client.post(
        "/api/auth/register",
        json={"email": "BUYER@example.com", "password": "another-password"},
    )

    assert duplicate.status_code == 409
    with context.session_factory() as session:
        assert session.query(context.main.models.Account).count() == 1


@pytest.mark.unit
def test_login_accepts_correct_password_and_rejects_wrong_password(
    service_client_factory,
):
    context = service_client_factory("auth-service")
    context.client.post(
        "/api/auth/register",
        json={"email": "buyer@example.com", "password": "valid-password"},
    )

    accepted = context.client.post(
        "/api/auth/login",
        json={"email": "buyer@example.com", "password": "valid-password"},
    )
    rejected = context.client.post(
        "/api/auth/login",
        json={"email": "buyer@example.com", "password": "wrong-password"},
    )

    assert accepted.status_code == 200
    assert accepted.json()["access_token"]
    assert rejected.status_code == 401


@pytest.mark.unit
@pytest.mark.parametrize(
    "credentials",
    [
        {"email": "not-an-email", "password": "valid-password"},
        {"email": "buyer@example.com", "password": "short"},
        {"email": "buyer@example.com", "password": "x" * 73},
    ],
)
def test_registration_rejects_invalid_credentials(
    service_client_factory,
    credentials,
):
    context = service_client_factory("auth-service")

    response = context.client.post("/api/auth/register", json=credentials)

    assert response.status_code == 422


@pytest.mark.unit
@pytest.mark.parametrize(
    "authorization",
    [
        None,
        "Bearer not-a-jwt",
        "Bearer "
        + jwt.encode(
            {
                "sub": "1",
                "role": "user",
                "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
            },
            "unit-test-only-secret",
            algorithm="HS256",
        ),
    ],
)
def test_verify_rejects_missing_invalid_and_expired_tokens(
    service_client_factory,
    authorization,
):
    context = service_client_factory("auth-service")
    headers = {"Authorization": authorization} if authorization else {}

    response = context.client.get("/api/auth/verify", headers=headers)

    assert response.status_code == 401


@pytest.mark.unit
def test_verify_returns_identity_for_valid_token(service_client_factory):
    context = service_client_factory("auth-service")
    registered = context.client.post(
        "/api/auth/register",
        json={"email": "buyer@example.com", "password": "valid-password"},
    )

    response = context.client.get(
        "/api/auth/verify",
        headers={"Authorization": f"Bearer {registered.json()['access_token']}"},
    )

    assert response.status_code == 200
    assert response.json() == {"user_id": 1, "role": "user"}
