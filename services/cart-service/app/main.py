import json

import httpx
import redis
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.responses import JSONResponse

from . import schemas
from .common import setup, request_id_var
from .config import settings

app = FastAPI(title="Cart Service")
log = setup(app, "cart-service")
r = redis.Redis.from_url(settings.redis_url, decode_responses=True)


@app.exception_handler(redis.RedisError)
async def redis_error(request, exc):
    log.error(f"Redis error: {exc!r}")
    return JSONResponse({"error": "Cart storage unavailable",
                         "request_id": request_id_var.get()}, status_code=503)


def current_user_id(x_user_id: str = Header(default="")) -> int:
    if not x_user_id.isdigit():
        raise HTTPException(401, "Authentication required")
    return int(x_user_id)


def key(user_id: int) -> str:
    return f"cart:{user_id}"


def fetch_product(product_id: int) -> dict:
    """Синхронный REST-вызов product-service."""
    try:
        resp = httpx.get(f"{settings.product_service_url}/api/products/{product_id}",
                         timeout=settings.http_timeout,
                         headers={"X-Request-ID": request_id_var.get()})
    except httpx.TimeoutException:
        log.error("product-service timeout")
        raise HTTPException(504, "Product service timeout")
    except httpx.HTTPError as e:
        log.error(f"product-service unreachable: {e!r}")
        raise HTTPException(502, "Product service unavailable")
    if resp.status_code == 404:
        raise HTTPException(404, "Product not found")
    if resp.status_code >= 400:
        raise HTTPException(502, "Product service error")
    return resp.json()


def fetch_stock(product_id: int) -> dict:
    """Read available stock from its owning service."""
    try:
        resp = httpx.get(
            f"{settings.inventory_service_url}/api/inventory/{product_id}",
            timeout=settings.http_timeout,
            headers={"X-Request-ID": request_id_var.get()},
        )
    except httpx.TimeoutException:
        log.error("inventory-service timeout")
        raise HTTPException(504, "Inventory service timeout")
    except httpx.HTTPError as e:
        log.error(f"inventory-service unreachable: {e!r}")
        raise HTTPException(502, "Inventory service unavailable")
    if resp.status_code >= 400:
        raise HTTPException(502, "Inventory service error")
    return resp.json()


def build_cart(user_id: int) -> schemas.CartOut:
    raw = r.hgetall(key(user_id))
    items = []
    for pid, value in raw.items():
        d = json.loads(value)
        items.append(schemas.CartItem(product_id=int(pid), **d))
    items.sort(key=lambda i: i.product_id)
    total = round(sum(i.price * i.quantity for i in items), 2)
    return schemas.CartOut(items=items, total=total)


@app.get("/api/cart", response_model=schemas.CartOut)
def get_cart(user_id: int = Depends(current_user_id)):
    return build_cart(user_id)


@app.post("/api/cart/items", response_model=schemas.CartOut)
def add_item(data: schemas.AddItem, user_id: int = Depends(current_user_id)):
    product = fetch_product(data.product_id)
    stock = fetch_stock(data.product_id)
    existing = r.hget(key(user_id), str(data.product_id))
    qty = data.quantity + (json.loads(existing)["quantity"] if existing else 0)
    if qty > stock["available"]:
        raise HTTPException(409, f"Only {stock['available']} in stock")
    r.hset(key(user_id), str(data.product_id), json.dumps(
        {"name": product["name"], "price": product["price"], "quantity": qty}))
    log.info(f"Cart updated user_id={user_id} product={data.product_id} qty={qty}")
    return build_cart(user_id)


@app.delete("/api/cart/items/{product_id}", response_model=schemas.CartOut)
def remove_item(product_id: int, user_id: int = Depends(current_user_id)):
    if not r.hdel(key(user_id), str(product_id)):
        raise HTTPException(404, "Item not in cart")
    return build_cart(user_id)


@app.delete("/api/cart", status_code=204)
def clear_cart(user_id: int = Depends(current_user_id)):
    r.delete(key(user_id))


# --- внутренние endpoint'ы для order-service ---

@app.get("/internal/cart/{user_id}", response_model=schemas.CartOut)
def internal_get(user_id: int):
    return build_cart(user_id)


@app.delete("/internal/cart/{user_id}", status_code=204)
def internal_clear(user_id: int):
    r.delete(key(user_id))
    log.info(f"Cart cleared user_id={user_id}")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    try:
        r.ping()
    except redis.RedisError:
        raise HTTPException(503, "Redis unavailable")
    return {"status": "ready"}
