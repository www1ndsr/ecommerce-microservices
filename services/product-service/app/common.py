import json, logging, time, uuid, contextvars
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

request_id_var = contextvars.ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    def __init__(self, service):
        super().__init__()
        self.service = service

    def format(self, r):
        return json.dumps({
            "timestamp": self.formatTime(r, "%Y-%m-%dT%H:%M:%S"),
            "service": self.service,
            "level": r.levelname,
            "request_id": request_id_var.get(),
            "message": r.getMessage(),
        }, ensure_ascii=False)


def setup(app, service):
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter(service))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    log = logging.getLogger(service)

    @app.middleware("http")
    async def request_middleware(request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request_id_var.set(rid)
        start = time.time()
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        ms = (time.time() - start) * 1000
        log.info(f"{request.method} {request.url.path} -> {response.status_code} ({ms:.0f}ms)")
        return response

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        return JSONResponse({"error": exc.detail, "request_id": request_id_var.get()},
                            status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        details = [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()]
        return JSONResponse({"error": "Invalid input", "details": details,
                             "request_id": request_id_var.get()}, status_code=422)

    @app.exception_handler(Exception)
    async def unhandled_error(request, exc):
        log.error(f"Unhandled error: {exc!r}")
        return JSONResponse({"error": "Internal server error",
                             "request_id": request_id_var.get()}, status_code=500)

    return log