import httpx
from fastapi import HTTPException, Request
from starlette.responses import Response

from .auth import authenticate, is_public_endpoint, require_admin
from .config import settings

_HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "proxy-connection",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}
_REQUEST_HEADERS_TO_DROP = _HOP_BY_HOP_HEADERS | {
    "host",
    "content-length",
    "x-user-id",
    "x-user-role",
    "x-request-id",
}
_RESPONSE_HEADERS_TO_DROP = _HOP_BY_HOP_HEADERS | {
    "content-encoding",
    "content-length",
    "x-request-id",
}


def _request_headers(request: Request, user_id: int | None,
                     role: str | None) -> list[tuple[str, str]]:
    connection_tokens = {
        token.strip().lower()
        for token in request.headers.get("connection", "").split(",")
        if token.strip()
    }
    excluded = _REQUEST_HEADERS_TO_DROP | connection_tokens
    headers = [
        (name.decode("latin-1"), value.decode("latin-1"))
        for name, value in request.scope["headers"]
        if name.decode("latin-1").lower() not in excluded
    ]
    headers.append(("X-Request-ID", request.state.request_id))
    if user_id is not None and role is not None:
        headers.append(("X-User-ID", str(user_id)))
        headers.append(("X-User-Role", role))
    return headers


def _response(request: Request, upstream: httpx.Response) -> Response:
    connection_tokens = {
        token.strip().lower()
        for token in upstream.headers.get("connection", "").split(",")
        if token.strip()
    }
    excluded = _RESPONSE_HEADERS_TO_DROP | connection_tokens
    response = Response(content=upstream.content, status_code=upstream.status_code)
    for name, value in upstream.headers.multi_items():
        if name.lower() not in excluded:
            response.headers.append(name, value)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


async def proxy_request(request: Request, service: str) -> Response:
    service_url = settings.service_urls.get(service)
    if service_url is None:
        raise HTTPException(status_code=404, detail="Service route not found")

    principal = None
    if not is_public_endpoint(request.method, request.url.path):
        principal = authenticate(request.headers.get("Authorization"))
        if service == "products" and request.method != "GET":
            require_admin(principal)

    url = f"{service_url}{request.url.path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"

    try:
        upstream = await request.app.state.http_client.request(
            method=request.method,
            url=url,
            headers=_request_headers(
                request,
                principal.user_id if principal else None,
                principal.role if principal else None,
            ),
            content=await request.body(),
        )
        return _response(request, upstream)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Upstream request timed out") from None
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Upstream service unavailable") from None
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Invalid upstream response") from None
