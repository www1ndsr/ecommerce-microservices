from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: str
    user_id: int
    order_id: int
    event_type: Literal["order.created", "payment.completed", "payment.failed"]
    title: str
    text: str
    created_at: datetime
    is_read: bool
