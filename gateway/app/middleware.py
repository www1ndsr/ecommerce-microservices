import asyncio
import time
import uuid
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .config import settings
from .logging_config import log_request, request_id_var

_RATE_LIMIT_EXEMPT = {
    "/health",
    "/ready",
    "/docs",
    "/redoc",
    "/openapi.json",
}


class InMemoryRateLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self.requests = defaultdict(deque)
        self.lock = asyncio.Lock()
        self.last_cleanup = 0.0

    async def allow(self, key: str) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        async with self.lock:
            if now - self.last_cleanup >= self.window_seconds:
                for client_key, entries in list(self.requests.items()):
                    while entries and entries[0] <= cutoff:
                        entries.popleft()
                    if not entries:
                        self.requests.pop(client_key, None)
                self.last_cleanup = now
            timestamps = self.requests[key]
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if len(timestamps) >= self.limit:
                retry_after = max(1, int(timestamps[0] + self.window_seconds - now))
                return False, retry_after
            timestamps.append(now)
            return True, 0


def add_gateway_middleware(app: FastAPI):
    limiter = InMemoryRateLimiter(
        settings.rate_limit_requests,
        settings.rate_limit_window_seconds,
    )
    app.state.rate_limiter = limiter

    @app.middleware("http")
    async def request_middleware(request: Request, call_next):
        incoming_id = request.headers.get("X-Request-ID", "")
        try:
            uuid.UUID(incoming_id)
            request_id = incoming_id
        except (ValueError, AttributeError):
            request_id = str(uuid.uuid4())

        request.state.request_id = request_id
        context_token = request_id_var.set(request_id)
        started = time.perf_counter()
        response = None

        try:
            client_host = request.client.host if request.client else "unknown"
            if (request.url.path not in _RATE_LIMIT_EXEMPT
                    and request.method != "OPTIONS"):
                allowed, retry_after = await limiter.allow(client_host)
                if not allowed:
                    response = JSONResponse(
                        {
                            "error": "Rate limit exceeded",
                            "request_id": request_id,
                        },
                        status_code=429,
                        headers={"Retry-After": str(retry_after)},
                    )
            if response is None:
                response = await call_next(request)
        except Exception as error:
            from .logging_config import logger

            logger.error(
                "Unhandled request error",
                extra={
                    "request_id": request_id,
                    "error_type": type(error).__name__,
                },
            )
            response = JSONResponse(
                {"error": "Internal server error", "request_id": request_id},
                status_code=500,
            )
        finally:
            if response is not None:
                response.headers["X-Request-ID"] = request_id
                log_request(
                    request_id,
                    request.method,
                    request.url.path,
                    response.status_code,
                    round((time.perf_counter() - started) * 1000, 2),
                )
            request_id_var.reset(context_token)

        return response
