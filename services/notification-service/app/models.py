import math
from datetime import datetime, timezone
from typing import TypedDict


EVENT_TYPES = {
    "order.created",
    "payment.completed",
    "payment.failed",
}


class InvalidEventError(ValueError):
    pass


class NotificationDocument(TypedDict):
    event_key: str
    user_id: int
    order_id: int
    event_type: str
    title: str
    text: str
    created_at: datetime
    is_read: bool


def from_event(event_type: str, payload: dict) -> NotificationDocument:
    if event_type not in EVENT_TYPES:
        raise InvalidEventError(f"Unsupported event type: {event_type}")

    user_id = payload.get("user_id")
    order_id = payload.get("order_id")
    if type(user_id) is not int or user_id < 1:
        raise InvalidEventError("Event user_id must be a positive integer")
    if type(order_id) is not int or order_id < 1:
        raise InvalidEventError("Event order_id must be a positive integer")

    amount_field = "total" if event_type == "order.created" else "amount"
    amount = payload.get(amount_field)
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        raise InvalidEventError(f"Event {amount_field} must be a non-negative number")
    try:
        amount_value = float(amount)
    except (OverflowError, ValueError):
        raise InvalidEventError(f"Event {amount_field} must be a finite number") from None
    if not math.isfinite(amount_value) or amount_value < 0:
        raise InvalidEventError(f"Event {amount_field} must be a finite non-negative number")

    if event_type == "order.created":
        title = "Заказ создан"
        message = f"Заказ №{order_id} создан. Сумма: {amount_value:.2f}."
    elif event_type == "payment.completed":
        title = "Оплата прошла"
        message = f"Оплата заказа №{order_id} на сумму {amount_value:.2f} прошла успешно."
    else:
        title = "Оплата не прошла"
        reason = payload.get("reason", "")
        if not isinstance(reason, str):
            raise InvalidEventError("Event reason must be a string")
        message = f"Оплата заказа №{order_id} на сумму {amount_value:.2f} отклонена."
        if reason:
            message = f"{message} Причина: {reason}"

    return {
        "event_key": f"{event_type}:{order_id}",
        "user_id": user_id,
        "order_id": order_id,
        "event_type": event_type,
        "title": title,
        "text": message,
        "created_at": datetime.now(timezone.utc),
        "is_read": False,
    }
