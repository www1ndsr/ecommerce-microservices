from pydantic import BaseModel, Field, ConfigDict


class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    price: float = Field(gt=0)
    stock: int = Field(ge=0)
    image_url: str = ""


class ProductOut(ProductIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
