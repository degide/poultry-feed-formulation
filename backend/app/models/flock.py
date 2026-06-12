"""Flock profile model.

Corresponds to `flocks`. A flock belongs to a user and has many formulations
over time. `previous_formulation_id` points at the most recently *validated*
formulation and is the anchor for the Dietary Transition Smoothness Index. The
NSGA-II second objective measures compositional distance from this formulation.

Note: `flocks` and `formulations` reference each other, creating a cyclic
foreign-key dependency. We mark this FK with `use_alter=True` so SQLAlchemy /
Alembic create the tables first and add the constraint afterwards.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.formulation import Formulation
    from app.models.user import User


class Flock(Base):
    __tablename__ = "flocks"

    flock_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # broiler | layer
    current_age_weeks: Mapped[int] = mapped_column(Integer, nullable=False)
    flock_size: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_formulation_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "formulations.formulation_id",
            ondelete="SET NULL",
            use_alter=True,  # break the flocks <-> formulations FK cycle
            name="fk_flocks_previous_formulation_id_formulations",
        ),
        nullable=True,
    )

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="flocks")
    formulations: Mapped[list["Formulation"]] = relationship(
        back_populates="flock",
        cascade="all, delete-orphan",
        foreign_keys="Formulation.flock_id",
    )
    previous_formulation: Mapped["Formulation | None"] = relationship(
        foreign_keys=[previous_formulation_id],
        post_update=True,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Flock id={self.flock_id} name={self.name!r} type={self.type!r}>"
