import time
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from . import models, schemas
from .common import setup
from .config import settings
from .db import Base, engine, get_db

ALLOWED_TRANSITIONS = {
    "CREATED": {"PROCESSING", "CANCELLED"},
    "PROCESSING": {"SHIPPED", "CANCELLED"},
    "SHIPPED": {"DELIVERED"},
    "DELIVERED": set(),
    "CANCELLED": set(),
}


@asynccontextmanager
async def lifespan(app):
    for attempt in range(20):
        try:
            Base.metadata.create_all(engine)
            break
        except SQLAlchemyError:
            if attempt == 19:
                raise RuntimeError("Shipping database unavailable during startup")
            time.sleep(2)
    yield


app = FastAPI(title="Shipping Service", lifespan=lifespan)
log = setup(app, "shipping-service")


def current_user_id(value: str) -> int:
    if not value.isdigit() or int(value) < 1:
        raise HTTPException(401, "Authentication required")
    return int(value)


def require_admin(role: str):
    if role != "admin":
        raise HTTPException(403, "Admin role required")


def get_shipment_or_404(db: Session, order_id: int) -> models.Shipment:
    shipment = db.scalar(
        select(models.Shipment).where(models.Shipment.order_id == order_id)
    )
    if shipment is None:
        raise HTTPException(404, "Shipment not found")
    return shipment


def to_out(shipment: models.Shipment) -> schemas.ShipmentOut:
    return schemas.ShipmentOut.model_validate(shipment)


def get_order(order_id: int, user_id: int, role: str, request_id: str):
    try:
        response = httpx.get(
            f"{settings.order_service_url}/api/orders/{order_id}",
            headers={"X-User-ID": str(user_id), "X-User-Role": role,
                     "X-Request-ID": request_id},
            timeout=settings.http_timeout,
        )
    except httpx.TimeoutException:
        log.error("Timeout calling Order Service for order_id=%s", order_id)
        raise HTTPException(504, "Order service timeout") from None
    except httpx.HTTPError:
        log.exception("Cannot reach Order Service for order_id=%s", order_id)
        raise HTTPException(502, "Order service unavailable") from None
    if response.status_code in (403, 404):
        raise HTTPException(response.status_code, "Order not found or access denied")
    if response.status_code != 200:
        raise HTTPException(502, "Order service error")
    order = response.json()
    if order.get("status") != "PAID":
        raise HTTPException(409, "Order is not ready for shipping")
    return order


@app.post("/api/shipping", response_model=schemas.ShipmentOut, status_code=201)
def create_shipment(
    data: schemas.ShipmentCreate,
    x_user_id: str = Header(default=""),
    x_user_role: str = Header(default="user"),
    x_request_id: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user_id = current_user_id(x_user_id)
    if db.scalar(select(models.Shipment.id).where(
        models.Shipment.order_id == data.order_id
    )):
        raise HTTPException(409, "Shipment already exists")
    order = get_order(data.order_id, user_id, x_user_role, x_request_id)
    owner_id = order.get("user_id")
    if not isinstance(owner_id, int) or owner_id < 1:
        raise HTTPException(502, "Invalid order response")
    shipment = models.Shipment(
        order_id=data.order_id, user_id=owner_id, address=data.address
    )
    db.add(shipment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Shipment already exists") from None
    db.refresh(shipment)
    log.info("Shipment created order_id=%s owner_id=%s", data.order_id, owner_id)
    return shipment


@app.get("/api/shipping", response_model=list[schemas.ShipmentOut])
def list_shipments(
    x_user_id: str = Header(default=""),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    user_id = current_user_id(x_user_id)
    return db.scalars(
        select(models.Shipment)
        .where(models.Shipment.user_id == user_id)
        .order_by(models.Shipment.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()


@app.get("/api/shipping/{order_id}", response_model=schemas.ShipmentOut)
def get_shipment(
    order_id: int,
    x_user_id: str = Header(default=""),
    x_user_role: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user_id = current_user_id(x_user_id)
    shipment = get_shipment_or_404(db, order_id)
    if shipment.user_id != user_id and x_user_role != "admin":
        raise HTTPException(403, "Access denied")
    return shipment


@app.patch("/api/shipping/{order_id}/status", response_model=schemas.ShipmentOut)
def update_status(
    order_id: int,
    data: schemas.ShipmentStatusUpdate,
    x_user_role: str = Header(default=""),
    db: Session = Depends(get_db),
):
    require_admin(x_user_role)
    shipment = get_shipment_or_404(db, order_id)
    if data.status not in ALLOWED_TRANSITIONS[shipment.status]:
        raise HTTPException(409, f"Cannot transition {shipment.status} to {data.status}")
    shipment.status = data.status
    db.commit()
    db.refresh(shipment)
    log.info("Shipment status changed order_id=%s status=%s", order_id, data.status)
    return shipment


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ready"}
