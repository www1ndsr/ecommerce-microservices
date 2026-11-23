from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PromotionCreate(BaseModel):
    code: str = Field(min_length=3, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    discount_percent: float = Field(gt=0, le=90)
    active: bool = True


class PromotionUpdate(BaseModel):
    discount_percent: float | None = Field(default=None, gt=0, le=90)
    active: bool | None = None


class PromotionCheck(BaseModel):
    code: str = Field(min_length=3, max_length=40)
    subtotal: float = Field(ge=0)


class PromotionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    discount_percent: float
    active: bool
    created_at: datetime


class PromotionQuote(BaseModel):
    code: str
    subtotal: float
    discount_percent: float
    discount_amount: float
    total: float
