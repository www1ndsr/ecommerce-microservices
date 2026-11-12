import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from . import models, schemas
from .common import setup
from .config import settings
from .db import Base, engine, get_db


@asynccontextmanager
async def lifespan(app):
    for _ in range(20):  # ждём, пока поднимется БД
        try:
            Base.metadata.create_all(engine)
            break
        except SQLAlchemyError:
            log.warning("DB not ready, retrying")
            time.sleep(2)
    yield


app = FastAPI(title="Auth Service", lifespan=lifespan)
log = setup(app, "auth-service")


def make_token(acc: models.Account) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(acc.id), "role": acc.role, "exp": exp}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


@app.post("/api/auth/register", response_model=schemas.TokenOut, status_code=201)
def register(data: schemas.Credentials, db: Session = Depends(get_db)):
    hashed = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()
    acc = models.Account(email=data.email.lower(), password_hash=hashed)
    db.add(acc)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email already registered")
    db.refresh(acc)
    log.info(f"User registered id={acc.id}")
    return schemas.TokenOut(access_token=make_token(acc))


@app.post("/api/auth/login", response_model=schemas.TokenOut)
def login(data: schemas.Credentials, db: Session = Depends(get_db)):
    acc = db.query(models.Account).filter_by(email=data.email.lower()).first()
    if not acc or not bcrypt.checkpw(data.password.encode(), acc.password_hash.encode()):
        log.warning("Failed login attempt")
        raise HTTPException(401, "Invalid email or password")
    log.info(f"User logged in id={acc.id}")
    return schemas.TokenOut(access_token=make_token(acc))


@app.get("/api/auth/verify", response_model=schemas.VerifyOut)
def verify(authorization: str = Header(default="")):
    token = authorization.removeprefix("Bearer ").strip()
    try:
        p = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return schemas.VerifyOut(user_id=int(p["sub"]), role=p["role"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")


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