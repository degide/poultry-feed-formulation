"""User account model.

Corresponds to the `users` table in the ERD. Passwords are never stored in
plaintext; `password_hash` holds a bcrypt hash (section 3.3, security).
Roles are stored as free-text to mirror the relational schema; allowed values
are enforced at the application/schema layer (farmer, feed_manager, admin).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.flock import Flock
    from app.models.market_price import MarketPrice


class User(Base, TimestampMixin):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # farmer | feed_manager | admin
    role: Mapped[str] = mapped_column(String(30), default="farmer", nullable=False)

    # Relationships
    flocks: Mapped[list["Flock"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    submitted_prices: Mapped[list["MarketPrice"]] = relationship(
        back_populates="entered_by",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.user_id} email={self.email!r} role={self.role!r}>"
