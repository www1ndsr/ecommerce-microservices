from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    rabbitmq_url: str
    max_amount: float = 3000.0  # заказы дороже этой суммы "отклоняются банком"


settings = Settings()