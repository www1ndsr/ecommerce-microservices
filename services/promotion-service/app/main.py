import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from . import models, schemas
from .common import setup
from .db import Base, engine, get_db


@asynccontextmanager
async def lifespan(app):
    for attempt in range(20):
        try:
            Base.metadata.create_all(engine)
            break
        except SQLAlchemyError:
            if attempt == 19:
                raise RuntimeError("Promotion database unavailable during startup")
            time.sleep(2)
    yield


app = FastAPI(title="Promotion Service", lifespan=lifespan)
log = setup(app, "promotion-service")


def require_admin(role: str):
    if role != "admin":
        raise HTTPException(403, "Admin role required")


def get_active_or_404(db: Session, code: str) -> models.Promotion:
    promotion = db.get(models.Promotion, code.upper())
    if promotion is None or not promotion.active:
        raise HTTPException(404, "Promotion not found or inactive")
    return promotion


def to_out(promotion: models.Promotion):
    return schemas.PromotionOut.model_validate(promotion)


@app.get("/api/promotions", response_model=list[schemas.PromotionOut])
def list_promotions(
    active_only: bool = True,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    statement = select(models.Promotion)
    if active_only:
        statement = statement.where(models.Promotion.active.is_(True))
    return db.scalars(
        statement.order_by(models.Promotion.code).offset(offset).limit(limit)
    ).all()


@app.get("/api/promotions/{code}", response_model=schemas.PromotionOut)
def get_promotion(code: str, db: Session = Depends(get_db)):
    return to_out(get_active_or_404(db, code))


@app.post("/api/promotions", response_model=schemas.PromotionOut, status_code=201)
def create_promotion(
    data: schemas.PromotionCreate,
    x_user_role: str = Header(default=""),
    db: Session = Depends(get_db),
):
    require_admin(x_user_role)
    promotion = models.Promotion(code=data.code.upper(), **data.model_dump(exclude={"code"}))
    db.add(promotion)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Promotion code already exists") from None
    db.refresh(promotion)
    log.info("Promotion created code=%s", promotion.code)
    return promotion


@app.patch("/api/promotions/{code}", response_model=schemas.PromotionOut)
def update_promotion(
    code: str,
    data: schemas.PromotionUpdate,
    x_user_role: str = Header(default=""),
    db: Session = Depends(get_db),
):
    require_admin(x_user_role)
    promotion = db.get(models.Promotion, code.upper())
    if promotion is None:
        raise HTTPException(404, "Promotion not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(promotion, field, value)
    db.commit()
    db.refresh(promotion)
    return promotion


@app.delete("/api/promotions/{code}", status_code=204)
def delete_promotion(
    code: str,
    x_user_role: str = Header(default=""),
    db: Session = Depends(get_db),
):
    require_admin(x_user_role)
    promotion = db.get(models.Promotion, code.upper())
    if promotion is None:
        raise HTTPException(404, "Promotion not found")
    db.delete(promotion)
    db.commit()
    log.info("Promotion deleted code=%s", code.upper())


@app.post("/api/promotions/validate", response_model=schemas.PromotionQuote)
def validate_promotion(data: schemas.PromotionCheck, db: Session = Depends(get_db)):
    promotion = get_active_or_404(db, data.code)
    discount = round(data.subtotal * promotion.discount_percent / 100, 2)
    return {
        "code": promotion.code,
        "subtotal": data.subtotal,
        "discount_percent": promotion.discount_percent,
        "discount_amount": discount,
        "total": round(data.subtotal - discount, 2),
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ready"}
