from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    order_id: int
    user_id: int
    amount: float
    status: str
    reason: str
    created_at: datetime