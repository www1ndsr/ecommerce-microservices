import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from . import models, schemas
from .common import setup
from .db import Base, engine, get_db


@asynccontextmanager
async def lifespan(app):
    for _ in range(20):
        try:
            Base.metadata.create_all(engine)
            break
        except SQLAlchemyError:
            log.warning("DB not ready, retrying")
            time.sleep(2)
    yield


app = FastAPI(title="User Service", lifespan=lifespan)
log = setup(app, "user-service")


def current_user_id(x_user_id: str = Header(default="")) -> int:
    # заголовок выставляет gateway после проверки JWT
    if not x_user_id.isdigit():
        raise HTTPException(401, "Authentication required")
    return int(x_user_id)


def get_or_create(db: Session, user_id: int) -> models.Profile:
    p = db.get(models.Profile, user_id)
    if not p:
        p = models.Profile(user_id=user_id)
        db.add(p)
        db.commit()
        db.refresh(p)
        log.info(f"Profile created user_id={user_id}")
    return p


@app.get("/api/users/me", response_model=schemas.ProfileOut)
def get_me(user_id: int = Depends(current_user_id), db: Session = Depends(get_db)):
    return get_or_create(db, user_id)


@app.put("/api/users/me", response_model=schemas.ProfileOut)
def update_me(data: schemas.ProfileIn, user_id: int = Depends(current_user_id),
              db: Session = Depends(get_db)):
    p = get_or_create(db, user_id)
    for k, v in data.model_dump().items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    log.info(f"Profile updated user_id={user_id}")
    return p


@app.get("/api/users/{target_id}", response_model=schemas.ProfileOut)
def get_user(target_id: int, user_id: int = Depends(current_user_id),
             x_user_role: str = Header(default=""), db: Session = Depends(get_db)):
    if target_id != user_id and x_user_role != "admin":
        raise HTTPException(403, "Access denied")
    p = db.get(models.Profile, target_id)
    if not p:
        raise HTTPException(404, "User not found")
    return p


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