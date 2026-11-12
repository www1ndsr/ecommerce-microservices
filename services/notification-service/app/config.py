from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongodb_url: str
    mongodb_database: str = "notifications"
    mongo_timeout_ms: int = 3000
    rabbitmq_url: str


settings = Settings()
