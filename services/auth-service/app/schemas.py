from pydantic import BaseModel, Field


class Credentials(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=6, max_length=72)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class VerifyOut(BaseModel):
    user_id: int
    role: str