from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


class Profile(Base):
    __tablename__ = "profiles"
    user_id: Mapped[int] = mapped_column(primary_key=True)  # id из auth-service
    full_name: Mapped[str] = mapped_column(String(200), default="")
    phone: Mapped[str] = mapped_column(String(30), default="")
    address: Mapped[str] = mapped_column(String(500), default="")