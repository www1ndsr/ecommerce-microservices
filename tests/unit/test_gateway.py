from datetime import datetime, timedelta, timezone

import httpx
import jwt
import pytest


class StubAsyncClient:
    is_closed = False

    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.requests = []

    async def request(self, *, method, url, headers, content):
        self.requests.append(
            {
                "method": method,
                "url": url,
                "headers": httpx.Headers(headers),
                "content": content,
            }
        )
        if self.error:
            raise self.error
        request = httpx.Request(method, url, headers=headers, content=content)
        return httpx.Response(
            self.response.status_code,
            headers=self.response.headers,
            content=self.response.content,
            request=request,
        )


def gateway_context(service_client_factory, *, response=None, error=None):
    context = service_client_factory("gateway")
    upstream = StubAsyncClient(
        response=response or httpx.Response(200, json={"ok": True}),
        error=error,
    )
    context.main.app.state.http_client = upstream
    return context, upstream


def token_for(role="user", *, expires_at=None, secret="unit-test-only-secret"):
    expires_at = expires_at or datetime.now(timezone.utc) + timedelta(minutes=5)
    return jwt.encode(
        {"sub": "23", "role": role, "exp": expires_at},
        secret,
        algorithm="HS256",
    )


@pytest.mark.unit
def test_public_product_get_is_forwarded_with_query_and_response_headers(
    service_client_factory,
):
    context, upstream = gateway_context(
        service_client_factory,
        response=httpx.Response(
            200,
            json=[{"id": 5}],
            headers={"X-Upstream": "product-service"},
        ),
    )

    response = context.client.get("/api/products?q=lamp&limit=1")

    assert response.status_code == 200
    assert response.json() == [{"id": 5}]
    assert response.headers["X-Upstream"] == "product-service"
    assert upstream.requests[0]["url"].endswith("/api/products?q=lamp&limit=1")


@pytest.mark.unit
def test_public_inventory_availability_is_forwarded_without_a_token(
    service_client_factory,
):
    context, upstream = gateway_context(service_client_factory)

    response = context.client.get("/api/inventory?product_ids=1,2")

    assert response.status_code == 200
    assert upstream.requests[0]["url"].startswith(
        "http://inventory-service:8000/api/inventory?product_ids=1,2"
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "path",
    [
        "/api/reviews?product_id=1",
        "/api/promotions/SAVE10",
        "/api/shipping/1",
        "/api/wishlist",
    ],
)
def test_new_business_service_routes_require_authentication(
    service_client_factory, path
):
    context, upstream = gateway_context(service_client_factory)

    response = context.client.get(path)

    assert response.status_code == 401
    assert upstream.requests == []


@pytest.mark.unit
def test_protected_route_rejects_missing_invalid_and_expired_tokens(
    service_client_factory,
):
    context, upstream = gateway_context(service_client_factory)
    expired = token_for(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))

    missing = context.client.get("/api/cart")
    invalid = context.client.get(
        "/api/cart",
        headers={"Authorization": "Bearer invalid"},
    )
    expired_response = context.client.get(
        "/api/cart",
        headers={"Authorization": f"Bearer {expired}"},
    )

    assert [missing.status_code, invalid.status_code, expired_response.status_code] == [
        401,
        401,
        401,
    ]
    assert upstream.requests == []


@pytest.mark.unit
def test_gateway_replaces_spoofed_identity_headers_with_jwt_claims(
    service_client_factory,
):
    context, upstream = gateway_context(service_client_factory)

    response = context.client.get(
        "/api/cart",
        headers={
            "Authorization": f"Bearer {token_for()}",
            "X-User-ID": "999",
            "X-User-Role": "admin",
            "X-Request-ID": "spoofed-request-id",
        },
    )

    forwarded = upstream.requests[0]["headers"]
    assert response.status_code == 200
    assert forwarded["X-User-ID"] == "23"
    assert forwarded["X-User-Role"] == "user"
    assert forwarded["X-Request-ID"] != "spoofed-request-id"


@pytest.mark.unit
def test_product_mutations_require_admin_role(service_client_factory):
    context, upstream = gateway_context(service_client_factory)
    payload = {"name": "Lamp"}

    forbidden = context.client.post(
        "/api/products",
        headers={"Authorization": f"Bearer {token_for('user')}"},
        json=payload,
    )
    accepted = context.client.post(
        "/api/products",
        headers={"Authorization": f"Bearer {token_for('admin')}"},
        json=payload,
    )

    assert forbidden.status_code == 403
    assert accepted.status_code == 200
    assert len(upstream.requests) == 1
    assert upstream.requests[0]["headers"]["X-User-Role"] == "admin"


@pytest.mark.unit
def test_gateway_reports_unavailable_upstream_and_readiness(
    service_client_factory,
):
    context, _ = gateway_context(
        service_client_factory,
        error=httpx.ConnectError("isolated upstream failure"),
    )

    unavailable = context.client.get(
        "/api/products",
        headers={"X-Request-ID": "test-request"},
    )

    assert unavailable.status_code == 503
    assert unavailable.json()["error"] == "Upstream service unavailable"
    assert unavailable.headers["X-Request-ID"]
    assert context.client.get("/health").json() == {"status": "ok"}
    assert context.client.get("/ready").json() == {"status": "ready"}
