import time
from contextlib import asynccontextmanager

import pika
from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from . import models, schemas, events
from .common import setup, request_id_var
from .config import settings
from .db import Base, engine, get_db, SessionLocal


@asynccontextmanager
async def lifespan(app):
    for _ in range(20):
        try:
            Base.metadata.create_all(engine)
            break
        except SQLAlchemyError:
            log.warning("DB not ready, retrying")
            time.sleep(2)
    else:
        raise RuntimeError("Database unavailable during startup")
    events.start_consumer(handle_order_created)
    yield


app = FastAPI(title="Payment Service", lifespan=lifespan)
log = setup(app, "payment-service")


def handle_order_created(data: dict):
    request_id_var.set(data.get("request_id", "-"))
    order_id, user_id, amount = data["order_id"], data["user_id"], data["total"]

    with SessionLocal() as db:
        if db.query(models.Payment).filter_by(order_id=order_id).first():
            log.info(f"Duplicate event for order {order_id}, skipped")
            return
        if amount > settings.max_amount:
            status, reason = "FAILED", "Amount exceeds limit"
        else:
            status, reason = "COMPLETED", ""
        db.add(models.Payment(order_id=order_id, user_id=user_id, amount=amount,
                              status=status, reason=reason))
        db.commit()
        log.info(f"Payment {status} for order {order_id}, amount={amount}")

    key = "payment.completed" if status == "COMPLETED" else "payment.failed"
    events.publish(key, {"order_id": order_id, "user_id": user_id,
                         "amount": amount, "reason": reason,
                         "request_id": request_id_var.get()})


@app.get("/api/payments/order/{order_id}", response_model=schemas.PaymentOut)
def get_payment(order_id: int, x_user_id: str = Header(default=""),
                x_user_role: str = Header(default=""), db: Session = Depends(get_db)):
    if not x_user_id.isdigit():
        raise HTTPException(401, "Authentication required")
    p = db.query(models.Payment).filter_by(order_id=order_id).first()
    if not p:
        raise HTTPException(404, "Payment not found")
    if p.user_id != int(x_user_id) and x_user_role != "admin":
        raise HTTPException(403, "Access denied")
    return p


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        events.check_connection()
    except (SQLAlchemyError, pika.exceptions.AMQPError, OSError) as e:
        log.warning(f"Dependency unavailable: {e!r}")
        raise HTTPException(503, "Database or RabbitMQ unavailable")
    return {"status": "ready"}