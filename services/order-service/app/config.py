from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    rabbitmq_url: str
    cart_service_url: str
    product_service_url: str
    http_timeout: float = 3.0


settings = Settings()