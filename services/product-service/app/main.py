import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Header, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from . import models, schemas
from .common import setup
from .db import Base, engine, get_db, SessionLocal

DEMO = [
    ("Ноутбук Pro 14", "Мощный ноутбук для работы", 1299.0, 15),
    ("Смартфон X", "Флагман с OLED-экраном", 799.0, 40),
    ("Наушники Air", "Беспроводные, шумоподавление", 199.0, 100),
    ("Механическая клавиатура", "Hot-swap, RGB", 89.0, 60),
    ("Монитор 27\" 4K", "IPS, 144 Гц", 449.0, 25),
    ("Умные часы", "Пульс, GPS, 7 дней работы", 249.0, 50),
]


@asynccontextmanager
async def lifespan(app):
    for _ in range(20):
        try:
            Base.metadata.create_all(engine)
            break
        except SQLAlchemyError:
            log.warning("DB not ready, retrying")
            time.sleep(2)
    with SessionLocal() as db:
        if db.query(models.Product).count() == 0:
            db.add_all([models.Product(name=n, description=d, price=p, stock=s)
                        for n, d, p, s in DEMO])
            db.commit()
            log.info("Demo products created")
    yield


app = FastAPI(title="Product Service", lifespan=lifespan)
log = setup(app, "product-service")


def require_admin(x_user_role: str = Header(default="")):
    # заголовок выставляет gateway после проверки JWT
    if x_user_role != "admin":
        raise HTTPException(403, "Admin role required")


def get_or_404(db: Session, product_id: int) -> models.Product:
    p = db.get(models.Product, product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    return p


@app.get("/api/products", response_model=list[schemas.ProductOut])
def list_products(q: str = "", limit: int = Query(50, le=100), offset: int = 0,
                  db: Session = Depends(get_db)):
    query = db.query(models.Product)
    if q:
        query = query.filter(models.Product.name.ilike(f"%{q}%"))
    return query.order_by(models.Product.id).offset(offset).limit(limit).all()


@app.get("/api/products/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, product_id)


@app.post("/api/products", response_model=schemas.ProductOut, status_code=201,
          dependencies=[Depends(require_admin)])
def create_product(data: schemas.ProductIn, db: Session = Depends(get_db)):
    p = models.Product(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    log.info(f"Product created id={p.id}")
    return p


@app.put("/api/products/{product_id}", response_model=schemas.ProductOut,
         dependencies=[Depends(require_admin)])
def update_product(product_id: int, data: schemas.ProductIn, db: Session = Depends(get_db)):
    p = get_or_404(db, product_id)
    for k, v in data.model_dump().items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p


@app.delete("/api/products/{product_id}", status_code=204,
            dependencies=[Depends(require_admin)])
def delete_product(product_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, product_id))
    db.commit()


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
