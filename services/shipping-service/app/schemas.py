from pydantic import BaseModel, ConfigDict, Field


class ShipmentCreate(BaseModel):
    order_id: int = Field(gt=0)
    address: str = Field(min_length=5, max_length=500)


class ShipmentStatusUpdate(BaseModel):
    status: str = Field(pattern=r"^(PROCESSING|SHIPPED|DELIVERED|CANCELLED)$")


class ShipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    user_id: int
    address: str
    status: str
