from fastapi import FastAPI, Request
from starlette.responses import Response

from .proxy import proxy_request

_HTTP_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")
_SERVICES = {
    "auth": "Authentication",
    "users": "User",
    "products": "Product",
    "cart": "Cart",
    "orders": "Order",
    "payments": "Payment",
    "notifications": "Notification",
}
def _make_endpoint(service: str, method: str, has_path: bool):
    if has_path:
        async def endpoint(
            request: Request,
            path: str,
        ) -> Response:
            return await proxy_request(request, service)
    else:
        async def endpoint(
            request: Request,
        ) -> Response:
            return await proxy_request(request, service)

    endpoint.__name__ = f"proxy_{service}_{method.lower()}_{'path' if has_path else 'root'}"
    endpoint.__doc__ = (
        f"Forward a {method} request to the {service} microservice. "
        "The original path, query string, headers and body are forwarded."
    )
    return endpoint


def register_routes(app: FastAPI):
    for service, title in _SERVICES.items():
        for method in _HTTP_METHODS:
            for has_path in (False, True):
                path = f"/api/{service}"
                if has_path:
                    path = f"{path}/{{path:path}}"
                openapi_extra = None
                if method in {"POST", "PUT", "PATCH"}:
                    openapi_extra = {
                        "requestBody": {
                            "required": False,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "additionalProperties": True,
                                    }
                                },
                                "application/octet-stream": {
                                    "schema": {
                                        "type": "string",
                                        "format": "binary",
                                    }
                                },
                            },
                        }
                    }
                app.add_api_route(
                    path,
                    _make_endpoint(service, method, has_path),
                    methods=[method],
                    name=f"proxy_{service}_{method.lower()}_{'path' if has_path else 'root'}",
                    summary=f"{method} {title} Service request",
                    description=(
                        f"Proxies to {service}-service. Authenticated requests "
                        "receive identity headers from the verified JWT; "
                        "client-supplied identity headers are discarded."
                    ),
                    response_class=Response,
                    tags=[f"{title} Service"],
                    openapi_extra=openapi_extra,
                )
