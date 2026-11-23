import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from . import models, schemas, events
from .common import setup, request_id_var
from .config import settings
from .db import Base, engine, get_db, SessionLocal

PRODUCT = settings.product_service_url
INVENTORY = settings.inventory_service_url
CART = settings.cart_service_url


@asynccontextmanager
async def lifespan(app):
    for _ in range(20):
        try:
            Base.metadata.create_all(engine)
            break
        except SQLAlchemyError:
            log.warning("DB not ready, retrying")
            time.sleep(2)
    events.start_consumer(handle_payment_event)
    yield


app = FastAPI(title="Order Service", lifespan=lifespan)
log = setup(app, "order-service")


def current_user_id(x_user_id: str = Header(default="")) -> int:
    if not x_user_id.isdigit():
        raise HTTPException(401, "Authentication required")
    return int(x_user_id)


def call(method: str, url: str, **kw) -> httpx.Response:
    """Синхронный вызов другого сервиса с маппингом ошибок."""
    try:
        return httpx.request(method, url, timeout=settings.http_timeout,
                             headers={"X-Request-ID": request_id_var.get()}, **kw)
    except httpx.TimeoutException:
        log.error(f"Timeout calling {url}")
        raise HTTPException(504, "Upstream service timeout")
    except httpx.HTTPError as e:
        log.error(f"Cannot reach {url}: {e!r}")
        raise HTTPException(502, "Upstream service unavailable")


def release(items):
    """Компенсация: вернуть зарезервированные товары на склад."""
    for it in items:
        pid, qty = (it["product_id"], it["quantity"]) if isinstance(it, dict) \
            else (it.product_id, it.quantity)
        try:
            call("POST", f"{INVENTORY}/internal/inventory/{pid}/release",
                 json={"quantity": qty})
        except HTTPException:
            log.error(f"Failed to release product {pid}")


def get_order_or_404(db: Session, order_id: int, user_id: int, role: str) -> models.Order:
    order = db.get(models.Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    if order.user_id != user_id and role != "admin":
        raise HTTPException(403, "Access denied")
    return order


@app.post("/api/orders", response_model=schemas.OrderOut, status_code=201)
def create_order(user_id: int = Depends(current_user_id), db: Session = Depends(get_db)):
    resp = call("GET", f"{CART}/internal/cart/{user_id}")
    if resp.status_code != 200:
        raise HTTPException(502, "Cart service error")
    cart = resp.json()
    if not cart["items"]:
        raise HTTPException(400, "Cart is empty")

    reserved = []
    try:
        for it in cart["items"]:
            r = call("POST", f"{INVENTORY}/internal/inventory/{it['product_id']}/reserve",
                     json={"quantity": it["quantity"]})
            if r.status_code == 409:
                raise HTTPException(409, f"Not enough stock: {it['name']}")
            if r.status_code != 200:
                raise HTTPException(502, "Product service error")
            reserved.append(it)
    except HTTPException:
        release(reserved)
        raise

    order = models.Order(user_id=user_id, total=cart["total"], items=[
        models.OrderItem(product_id=i["product_id"], name=i["name"],
                         price=i["price"], quantity=i["quantity"])
        for i in cart["items"]])
    try:
        db.add(order)
        db.commit()
        db.refresh(order)
    except SQLAlchemyError as e:
        db.rollback()
        log.error(f"DB error while saving order: {e!r}")
        release(reserved)
        raise HTTPException(503, "Could not save order")

    try:
        call("DELETE", f"{CART}/internal/cart/{user_id}")
    except HTTPException:
        log.warning("Cart was not cleared")

    try:
        events.publish("order.created", {
            "order_id": order.id, "user_id": user_id, "total": order.total,
            "items": cart["items"], "request_id": request_id_var.get()})
        log.info(f"Order created id={order.id}, event published")
    except Exception as e:
        log.error(f"Failed to publish order.created: {e!r}")
    return order


@app.get("/api/orders", response_model=list[schemas.OrderOut])
def my_orders(user_id: int = Depends(current_user_id), db: Session = Depends(get_db)):
    return (db.query(models.Order).filter_by(user_id=user_id)
            .order_by(models.Order.id.desc()).all())


@app.get("/api/orders/{order_id}", response_model=schemas.OrderOut)
def get_order(order_id: int, user_id: int = Depends(current_user_id),
              x_user_role: str = Header(default=""), db: Session = Depends(get_db)):
    return get_order_or_404(db, order_id, user_id, x_user_role)


@app.post("/api/orders/{order_id}/cancel", response_model=schemas.OrderOut)
def cancel_order(order_id: int, user_id: int = Depends(current_user_id),
                 x_user_role: str = Header(default=""), db: Session = Depends(get_db)):
    order = get_order_or_404(db, order_id, user_id, x_user_role)
    if order.status != "PENDING":
        raise HTTPException(409, f"Cannot cancel order in status {order.status}")
    order.status = "CANCELLED"
    db.commit()
    release(order.items)
    try:
        events.publish("order.cancelled", {"order_id": order.id, "user_id": order.user_id})
    except Exception as e:
        log.error(f"Failed to publish order.cancelled: {e!r}")
    log.info(f"Order cancelled id={order.id}")
    return order


def handle_payment_event(routing_key: str, data: dict):
    with SessionLocal() as db:
        order = db.get(models.Order, data["order_id"])
        if not order or order.status != "PENDING":
            return
        if routing_key == "payment.completed":
            order.status = "PAID"
        elif routing_key == "payment.failed":
            order.status = "PAYMENT_FAILED"
            release(order.items)
        db.commit()
        log.info(f"Order {order.id} -> {order.status}")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(503, "Database unavailable")
    return {"status": "ready"}
