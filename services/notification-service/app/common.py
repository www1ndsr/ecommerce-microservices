import os
import contextvars
import json
import logging
import time
import uuid

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

request_id_var = contextvars.ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    def __init__(self, service):
        super().__init__()
        self.service = service

    def format(self, record):
        return json.dumps({
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "service": self.service,
            "level": record.levelname,
            "request_id": request_id_var.get(),
            "message": record.getMessage(),
        }, ensure_ascii=False)


def setup(app, service):
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter(service))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    log = logging.getLogger(service)

    @app.middleware("http")
    async def request_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request_id_var.set(request_id)
        started = time.time()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        elapsed_ms = (time.time() - started) * 1000
        log.info(
            f"{request.method} {request.url.path} -> "
            f"{response.status_code} ({elapsed_ms:.0f}ms)"
        )
        return response

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        return JSONResponse(
            {"error": exc.detail, "request_id": request_id_var.get()},
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        details = [
            f"{'.'.join(map(str, error['loc']))}: {error['msg']}"
            for error in exc.errors()
        ]
        return JSONResponse(
            {
                "error": "Invalid input",
                "details": details,
                "request_id": request_id_var.get(),
            },
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def unhandled_error(request, exc):
        log.error(f"Unhandled error: {exc!r}")
        return JSONResponse(
            {
                "error": "Internal server error",
                "request_id": request_id_var.get(),
            },
            status_code=500,
        )

    return log
