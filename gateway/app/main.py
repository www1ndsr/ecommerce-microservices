from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings
from .logging_config import configure_logging
from .middleware import add_gateway_middleware
from .routes import register_routes

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    timeout = httpx.Timeout(settings.upstream_timeout_seconds)
    app.state.http_client = httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=False,
    )
    try:
        yield
    finally:
        await app.state.http_client.aclose()


app = FastAPI(
    title="E-commerce API Gateway",
    description=(
        "Single HTTP entry point for the e-commerce microservices. "
        "Protected requests require the Auth Service HS256 Bearer JWT."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

add_gateway_middleware(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)
register_routes(app)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema.setdefault("components", {}).setdefault("securitySchemes", {})[
        "BearerAuth"
    ] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    for path, path_item in schema["paths"].items():
        if not path.startswith("/api/"):
            continue
        for operation in path_item.values():
            if isinstance(operation, dict) and "operationId" in operation:
                operation["security"] = [{"BearerAuth": []}, {}]
                operation["description"] = (
                    f"{operation.get('description', '')} "
                    "Authenticate in Swagger with a Bearer JWT. "
                    "Registration, login and public product GET routes "
                    "do not require a token."
                ).strip()

    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        {
            "error": exc.detail,
            "request_id": getattr(request.state, "request_id", "-"),
        },
        status_code=exc.status_code,
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    details = [
        f"{'.'.join(map(str, error['loc']))}: {error['msg']}"
        for error in exc.errors()
    ]
    return JSONResponse(
        {
            "error": "Invalid request",
            "details": details,
            "request_id": getattr(request.state, "request_id", "-"),
        },
        status_code=422,
    )


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    from .logging_config import logger

    logger.error(
        "Unhandled gateway exception",
        extra={
            "request_id": getattr(request.state, "request_id", "-"),
            "error_type": type(exc).__name__,
        },
    )
    return JSONResponse(
        {
            "error": "Internal server error",
            "request_id": getattr(request.state, "request_id", "-"),
        },
        status_code=500,
    )


@app.get("/health", tags=["Health"], summary="Gateway liveness")
async def health():
    return {"status": "ok"}


@app.get("/ready", tags=["Health"], summary="Gateway readiness")
async def ready(request: Request):
    client = getattr(request.app.state, "http_client", None)
    if client is None or client.is_closed:
        raise HTTPException(status_code=503, detail="Gateway is not ready")
    return {"status": "ready"}
