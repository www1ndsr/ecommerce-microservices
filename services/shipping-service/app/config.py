from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    order_service_url: str = "http://order-service:8000"
    http_timeout: float = Field(default=3.0, gt=0)


settings = Settings()
