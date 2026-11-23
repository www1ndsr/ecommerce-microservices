import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from sqlalchemy import select, text, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from . import models, schemas
from .common import setup
from .db import Base, SessionLocal, engine, get_db

DEMO_STOCK = {1: 15, 2: 40, 3: 100, 4: 60, 5: 25, 6: 50}


@asynccontextmanager
async def lifespan(app):
    for attempt in range(20):
        try:
            Base.metadata.create_all(engine)
            with SessionLocal() as db:
                if db.query(models.Stock).count() == 0:
                    db.add_all([
                        models.Stock(product_id=product_id, available=quantity, reserved=0)
                        for product_id, quantity in DEMO_STOCK.items()
                    ])
                    db.commit()
            break
        except SQLAlchemyError:
            if attempt == 19:
                raise RuntimeError("Inventory database unavailable during startup")
            time.sleep(2)
    yield


app = FastAPI(title="Inventory Service", lifespan=lifespan)
log = setup(app, "inventory-service")


def require_admin(role: str):
    if role != "admin":
        raise HTTPException(403, "Admin role required")


def get_stock_or_default(db: Session, product_id: int):
    row = db.get(models.Stock, product_id)
    return row or models.Stock(product_id=product_id, available=0, reserved=0)


@app.get("/api/inventory", response_model=list[schemas.StockOut])
def list_stock(product_ids: str = Query(default=""), db: Session = Depends(get_db)):
    ids = []
    if product_ids:
        try:
            ids = [int(value) for value in product_ids.split(",")]
        except ValueError:
            raise HTTPException(422, "Invalid product_ids") from None
        if any(product_id < 1 for product_id in ids):
            raise HTTPException(422, "Invalid product_ids")
    if not ids:
        return db.scalars(select(models.Stock).order_by(models.Stock.product_id)).all()
    rows = db.scalars(
        select(models.Stock).where(models.Stock.product_id.in_(ids))
    ).all()
    by_id = {row.product_id: row for row in rows}
    return [
        by_id[product_id] if product_id in by_id else {
            "product_id": product_id, "available": 0, "reserved": 0
        }
        for product_id in ids
    ]


@app.get("/api/inventory/{product_id}", response_model=schemas.StockOut)
def get_stock(product_id: int, db: Session = Depends(get_db)):
    return get_stock_or_default(db, product_id)


@app.put("/api/inventory/{product_id}", response_model=schemas.StockOut)
def set_stock(
    product_id: int,
    data: schemas.StockSet,
    x_user_role: str = Header(default=""),
    db: Session = Depends(get_db),
):
    if x_user_role != "admin":
        raise HTTPException(403, "Admin role required")
    row = db.get(models.Stock, product_id)
    if row is None:
        row = models.Stock(product_id=product_id, available=data.quantity, reserved=0)
        db.add(row)
    else:
        row.available = data.quantity
    db.commit()
    db.refresh(row)
    log.info("Stock level changed product_id=%s available=%s", product_id, row.available)
    return row


def change_stock(product_id: int, quantity: int, *, reserve: bool, db: Session):
    if reserve:
        statement = (
            update(models.Stock)
            .where(models.Stock.product_id == product_id,
                   models.Stock.available >= quantity)
            .values(available=models.Stock.available - quantity,
                    reserved=models.Stock.reserved + quantity)
        )
    else:
        statement = (
            update(models.Stock)
            .where(models.Stock.product_id == product_id,
                   models.Stock.reserved >= quantity)
            .values(available=models.Stock.available + quantity,
                    reserved=models.Stock.reserved - quantity)
        )
    result = db.execute(statement)
    if result.rowcount == 0:
        db.rollback()
        if db.get(models.Stock, product_id) is None:
            raise HTTPException(404, "Inventory record not found")
        raise HTTPException(409, "Insufficient stock or reservation")
    db.commit()
    row = db.get(models.Stock, product_id)
    log.info("%s quantity=%s product_id=%s", "Reserved" if reserve else "Released",
             quantity, product_id)
    return row


@app.post("/internal/inventory/{product_id}/reserve", response_model=schemas.StockOut)
def reserve(product_id: int, data: schemas.StockChange, db: Session = Depends(get_db)):
    return change_stock(product_id, data.quantity, reserve=True, db=db)


@app.post("/internal/inventory/{product_id}/release", response_model=schemas.StockOut)
def release(product_id: int, data: schemas.StockChange, db: Session = Depends(get_db)):
    return change_stock(product_id, data.quantity, reserve=False, db=db)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ready"}
