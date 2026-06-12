"""Formulation models.

Contains three tables:

* `formulations`            - one generated ration (cost + DTSI scores, method).
* `formulation_ingredients` - junction: which ingredients and at what % (M:N).
* `formulation_price_snapshots` - junction: the exact price rows used, so a
                                  formulation remains reproducible even after
                                  prices change (rolling price log).

`generated_by` records whether the ration came from the NSGA-II engine or the
LP baseline.
"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Enum as SAEnum,
    Float,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.flock import Flock
    from app.models.ingredient import Ingredient
    from app.models.market_price import MarketPrice


class FormulationMethod(str, enum.Enum):
    """Maps to the `formulation_method` enum in the ERD."""

    NSGA_II = "NSGA-II"
    LP = "LP"


class Formulation(Base, TimestampMixin):
    __tablename__ = "formulations"

    formulation_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    flock_id: Mapped[int] = mapped_column(
        ForeignKey("flocks.flock_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    total_cost_per_kg_rwf: Mapped[float] = mapped_column(Float, nullable=False)
    dtsi_score: Mapped[float] = mapped_column(Float, nullable=False)
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    generated_by: Mapped[FormulationMethod] = mapped_column(
        SAEnum(FormulationMethod, name="formulation_method"),
        nullable=False,
    )

    # Relationships
    flock: Mapped["Flock"] = relationship(
        back_populates="formulations",
        foreign_keys=[flock_id],
    )
    ingredients: Mapped[list["FormulationIngredient"]] = relationship(
        back_populates="formulation",
        cascade="all, delete-orphan",
    )
    price_snapshots: Mapped[list["FormulationPriceSnapshot"]] = relationship(
        back_populates="formulation",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Formulation id={self.formulation_id} method={self.generated_by.value} "
            f"cost={self.total_cost_per_kg_rwf:.2f} dtsi={self.dtsi_score:.4f}>"
        )


class FormulationIngredient(Base):
    """Junction table: ingredient proportions within a formulation."""

    __tablename__ = "formulation_ingredients"

    formulation_id: Mapped[int] = mapped_column(
        ForeignKey("formulations.formulation_id", ondelete="CASCADE"),
        primary_key=True,
    )
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.ingredient_id", ondelete="CASCADE"),
        primary_key=True,
    )
    proportion_percent: Mapped[float] = mapped_column(Float, nullable=False)

    formulation: Mapped["Formulation"] = relationship(back_populates="ingredients")
    ingredient: Mapped["Ingredient"] = relationship(back_populates="formulation_links")

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<FormulationIngredient f={self.formulation_id} i={self.ingredient_id} "
            f"{self.proportion_percent:.2f}%>"
        )


class FormulationPriceSnapshot(Base):
    """Junction table: the market-price rows that fed a formulation."""

    __tablename__ = "formulation_price_snapshots"

    formulation_id: Mapped[int] = mapped_column(
        ForeignKey("formulations.formulation_id", ondelete="CASCADE"),
        primary_key=True,
    )
    price_id: Mapped[int] = mapped_column(
        ForeignKey("market_prices.price_id", ondelete="CASCADE"),
        primary_key=True,
    )

    formulation: Mapped["Formulation"] = relationship(back_populates="price_snapshots")
    market_price: Mapped["MarketPrice"] = relationship(back_populates="snapshot_links")

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<FormulationPriceSnapshot f={self.formulation_id} p={self.price_id}>"
        )
