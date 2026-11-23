from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Stock(Base):
    __tablename__ = "inventory"

    product_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    available: Mapped[int] = mapped_column(Integer, default=0)
    reserved: Mapped[int] = mapped_column(Integer, default=0)
