from pydantic import BaseModel, Field


class AddItem(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=99)


class CartItem(BaseModel):
    product_id: int
    name: str
    price: float
    quantity: int


class CartOut(BaseModel):
    items: list[CartItem]
    total: float