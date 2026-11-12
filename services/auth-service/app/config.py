from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    jwt_secret: str = "change-me"
    jwt_expire_minutes: int = 60


settings = Settings()