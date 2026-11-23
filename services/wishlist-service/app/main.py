import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from sqlalchemy import delete, select, text
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
                raise RuntimeError("Wishlist database unavailable during startup")
            time.sleep(2)
    yield


app = FastAPI(title="Wishlist Service", lifespan=lifespan)
log = setup(app, "wishlist-service")


def current_user_id(value: str) -> int:
    if not value.isdigit() or int(value) < 1:
        raise HTTPException(401, "Authentication required")
    return int(value)


@app.get("/api/wishlist", response_model=list[schemas.WishlistItemOut])
def get_wishlist(
    x_user_id: str = Header(default=""),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    user_id = current_user_id(x_user_id)
    return db.scalars(
        select(models.WishlistItem)
        .where(models.WishlistItem.user_id == user_id)
        .order_by(models.WishlistItem.created_at.desc(), models.WishlistItem.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()


@app.post("/api/wishlist", response_model=schemas.WishlistItemOut, status_code=201)
def add_to_wishlist(
    data: schemas.WishlistItemCreate,
    x_user_id: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user_id = current_user_id(x_user_id)
    item = db.scalar(select(models.WishlistItem).where(
        models.WishlistItem.user_id == user_id,
        models.WishlistItem.product_id == data.product_id,
    ))
    if item is not None:
        return item
    item = models.WishlistItem(user_id=user_id, product_id=data.product_id)
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        item = db.scalar(select(models.WishlistItem).where(
            models.WishlistItem.user_id == user_id,
            models.WishlistItem.product_id == data.product_id,
        ))
        if item is None:
            raise HTTPException(409, "Could not add item to wishlist") from None
        return item
    db.refresh(item)
    log.info("Wishlist item added user_id=%s product_id=%s", user_id, item.product_id)
    return item


@app.delete("/api/wishlist/{product_id}", status_code=204)
def remove_from_wishlist(
    product_id: int,
    x_user_id: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user_id = current_user_id(x_user_id)
    result = db.execute(delete(models.WishlistItem).where(
        models.WishlistItem.user_id == user_id,
        models.WishlistItem.product_id == product_id,
    ))
    if result.rowcount == 0:
        raise HTTPException(404, "Wishlist item not found")
    db.commit()
    log.info("Wishlist item removed user_id=%s product_id=%s", user_id, product_id)


@app.delete("/api/wishlist", status_code=204)
def clear_wishlist(
    x_user_id: str = Header(default=""),
    db: Session = Depends(get_db),
):
    user_id = current_user_id(x_user_id)
    db.execute(delete(models.WishlistItem).where(models.WishlistItem.user_id == user_id))
    db.commit()
    log.info("Wishlist cleared user_id=%s", user_id)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ready"}
