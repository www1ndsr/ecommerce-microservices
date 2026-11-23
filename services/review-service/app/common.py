import contextvars
import json
import logging
import time
import uuid
from datetime import datetime, timezone

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

request_id_var = contextvars.ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    def __init__(self, service: str):
        super().__init__()
        self.service = service

    def format(self, record):
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": self.service,
            "level": record.levelname,
            "request_id": getattr(record, "request_id", request_id_var.get()),
            "message": record.getMessage(),
        }
        payload.update(getattr(record, "structured_fields", {}))
        return json.dumps(payload, ensure_ascii=False)


def setup(app, service: str):
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter(service))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    log = logging.getLogger(service)

    def write(level: str, request_id: str, message: str, **fields):
        log.log(getattr(logging, level), message,
                extra={"request_id": request_id, "structured_fields": fields})

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            write("INFO", request_id, "HTTP request", method=request.method,
                  path=request.url.path, status=response.status_code,
                  duration_ms=round((time.perf_counter() - started) * 1000, 2))
            return response
        except Exception:
            write("ERROR", request_id, "Unhandled request error")
            raise
        finally:
            request_id_var.reset(token)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        request_id = request_id_var.get()
        return JSONResponse({"error": exc.detail, "request_id": request_id},
                            status_code=exc.status_code, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        details = [f"{'.'.join(map(str, error['loc']))}: {error['msg']}"
                   for error in exc.errors()]
        return JSONResponse({"error": "Invalid input", "details": details,
                             "request_id": request_id_var.get()}, status_code=422)

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, exc):
        request_id = request_id_var.get()
        write("ERROR", request_id, "Database error", error_type=type(exc).__name__)
        return JSONResponse({"error": "Database unavailable", "request_id": request_id},
                            status_code=503)

    @app.exception_handler(Exception)
    async def unhandled_error(request, exc):
        request_id = request_id_var.get()
        write("ERROR", request_id, "Unhandled application error",
              error_type=type(exc).__name__)
        return JSONResponse({"error": "Internal server error", "request_id": request_id},
                            status_code=500)

    return log
