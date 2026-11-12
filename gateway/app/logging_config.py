import contextvars
import json
import logging
from datetime import datetime, timezone

request_id_var = contextvars.ContextVar("gateway_request_id", default="-")
logger = logging.getLogger("api-gateway")


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(timespec="milliseconds"),
            "service": "api-gateway",
            "level": record.levelname,
            "request_id": getattr(record, "request_id", request_id_var.get()),
            "message": record.getMessage(),
        }
        for field in ("method", "endpoint", "status", "duration_ms", "error_type"):
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


def log_request(request_id: str, method: str, endpoint: str,
                status: int, duration_ms: float):
    logger.info(
        "http_request",
        extra={
            "request_id": request_id,
            "method": method,
            "endpoint": endpoint,
            "status": status,
            "duration_ms": duration_ms,
        },
    )
