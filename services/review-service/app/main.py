import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from sqlalchemy import func, select, text
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
                raise RuntimeError("Review database unavailable during startup")
            time.sleep(2)
    yield


app = FastAPI(title="Review Service", lifespan=lifespan)
log = setup(app, "review-service")


def current_user_id(value: str) -> int:
    if not value.isdigit() or int(value) < 1:
        raise HTTPException(401, "Authentication required")
    return int(value)


def get_review_or_404(db: Session, review_id: int) -> models.Review:
    review = db.get(models.Review, review_id)
    if review is None:
        raise HTTPException(404, "Review not found")
    return review


@app.post("/api/reviews", response_model=schemas.ReviewOut, status_code=201)
def create_review(
    data: schemas.ReviewCreate,
    x_user_id: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user_id = current_user_id(x_user_id)
    review = models.Review(user_id=user_id, **data.model_dump())
    db.add(review)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "You have already reviewed this product") from None
    db.refresh(review)
    log.info("Review created id=%s product_id=%s user_id=%s",
             review.id, review.product_id, user_id)
    return review


@app.get("/api/reviews", response_model=list[schemas.ReviewOut])
def list_reviews(
    product_id: int = Query(gt=0),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(models.Review)
        .where(models.Review.product_id == product_id)
        .order_by(models.Review.created_at.desc(), models.Review.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()


@app.get("/api/reviews/summary/{product_id}", response_model=schemas.ReviewSummary)
def review_summary(product_id: int, db: Session = Depends(get_db)):
    if product_id < 1:
        raise HTTPException(422, "product_id must be positive")
    average, count = db.execute(
        select(func.avg(models.Review.rating), func.count(models.Review.id))
        .where(models.Review.product_id == product_id)
    ).one()
    return {"product_id": product_id, "average_rating": round(average or 0, 2),
            "review_count": count}


@app.put("/api/reviews/{review_id}", response_model=schemas.ReviewOut)
def update_review(
    review_id: int,
    data: schemas.ReviewUpdate,
    x_user_id: str = Header(default=""),
    x_user_role: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user_id = current_user_id(x_user_id)
    review = get_review_or_404(db, review_id)
    if review.user_id != user_id and x_user_role != "admin":
        raise HTTPException(403, "Access denied")
    for field, value in data.model_dump().items():
        setattr(review, field, value)
    db.commit()
    db.refresh(review)
    return review


@app.delete("/api/reviews/{review_id}", status_code=204)
def delete_review(
    review_id: int,
    x_user_id: str = Header(default=""),
    x_user_role: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user_id = current_user_id(x_user_id)
    review = get_review_or_404(db, review_id)
    if review.user_id != user_id and x_user_role != "admin":
        raise HTTPException(403, "Access denied")
    db.delete(review)
    db.commit()
    log.info("Review deleted id=%s user_id=%s", review_id, user_id)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ready"}
