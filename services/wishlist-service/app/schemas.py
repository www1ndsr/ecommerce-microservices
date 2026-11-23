from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WishlistItemCreate(BaseModel):
    product_id: int = Field(gt=0)


class WishlistItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    product_id: int
    created_at: datetime
