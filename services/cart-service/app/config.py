from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str
    product_service_url: str
    http_timeout: float = 3.0


settings = Settings()