from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    favorite_categories: Mapped[list["FavoriteCategory"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class FavoriteCategory(Base):
    __tablename__ = "favorite_categories"
    __table_args__ = (UniqueConstraint("user_id", "category", name="uq_user_category"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    category: Mapped[str] = mapped_column(String(50), index=True)

    user: Mapped[User] = relationship(back_populates="favorite_categories")
