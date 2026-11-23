from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str
    product_service_url: str
    inventory_service_url: str = "http://inventory-service:8000"
    http_timeout: float = 3.0


settings = Settings()
