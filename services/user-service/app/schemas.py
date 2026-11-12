from pydantic import BaseModel, Field, ConfigDict


class ProfileIn(BaseModel):
    full_name: str = Field(default="", max_length=200)
    phone: str = Field(default="", pattern=r"^[0-9+\-\s()]{0,30}$")
    address: str = Field(default="", max_length=500)


class ProfileOut(ProfileIn):
    model_config = ConfigDict(from_attributes=True)
    user_id: int