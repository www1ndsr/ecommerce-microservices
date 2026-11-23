from pydantic import BaseModel, ConfigDict, Field


class StockSet(BaseModel):
    quantity: int = Field(ge=0)


class StockChange(BaseModel):
    quantity: int = Field(gt=0)


class StockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    available: int
    reserved: int
