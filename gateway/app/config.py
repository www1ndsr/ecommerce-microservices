from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    jwt_secret: SecretStr

    auth_service_url: str = "http://auth-service:8000"
    user_service_url: str = "http://user-service:8000"
    product_service_url: str = "http://product-service:8000"
    cart_service_url: str = "http://cart-service:8000"
    order_service_url: str = "http://order-service:8000"
    payment_service_url: str = "http://payment-service:8000"
    notification_service_url: str = "http://notification-service:8000"
    inventory_service_url: str = "http://inventory-service:8000"
    review_service_url: str = "http://review-service:8000"
    promotion_service_url: str = "http://promotion-service:8000"
    shipping_service_url: str = "http://shipping-service:8000"
    wishlist_service_url: str = "http://wishlist-service:8000"

    upstream_timeout_seconds: float = Field(default=10.0, gt=0)
    rate_limit_requests: int = Field(default=120, ge=1)
    rate_limit_window_seconds: int = Field(default=60, ge=1)
    cors_origins: str = "http://localhost:3000"

    @property
    def service_urls(self) -> dict[str, str]:
        return {
            "auth": self.auth_service_url.rstrip("/"),
            "users": self.user_service_url.rstrip("/"),
            "products": self.product_service_url.rstrip("/"),
            "cart": self.cart_service_url.rstrip("/"),
            "orders": self.order_service_url.rstrip("/"),
            "payments": self.payment_service_url.rstrip("/"),
            "notifications": self.notification_service_url.rstrip("/"),
            "inventory": self.inventory_service_url.rstrip("/"),
            "reviews": self.review_service_url.rstrip("/"),
            "promotions": self.promotion_service_url.rstrip("/"),
            "shipping": self.shipping_service_url.rstrip("/"),
            "wishlist": self.wishlist_service_url.rstrip("/"),
        }

    @property
    def allowed_origins(self) -> list[str]:
        origins = [
            origin.strip().rstrip("/")
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]
        if "*" in origins:
            raise ValueError("CORS_ORIGINS must not contain '*' with credentials enabled")
        return origins


settings = Settings()
