from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    rabbitmq_url: str
    cart_service_url: str
    product_service_url: str
    inventory_service_url: str = "http://inventory-service:8000"
    http_timeout: float = 3.0


settings = Settings()
