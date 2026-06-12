"""Feed ingredient model.

Corresponds to the `ingredients` table. The 12 ingredients of the validated
library are stored here; their nutrient values live
in `nutritional_compositions`, and their prices in `market_prices`.
`is_active` lets an administrator retire an ingredient without deleting history.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.formulation import FormulationIngredient
    from app.models.market_price import MarketPrice
    from app.models.nutritional_composition import NutritionalComposition


class Ingredient(Base):
    __tablename__ = "ingredients"

    ingredient_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    # e.g. energy_source | protein_source | mineral | additive | premix
    category: Mapped[str] = mapped_column(String(60), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    nutritional_compositions: Mapped[list["NutritionalComposition"]] = relationship(
        back_populates="ingredient",
        cascade="all, delete-orphan",
    )
    market_prices: Mapped[list["MarketPrice"]] = relationship(
        back_populates="ingredient",
        cascade="all, delete-orphan",
    )
    formulation_links: Mapped[list["FormulationIngredient"]] = relationship(
        back_populates="ingredient",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Ingredient id={self.ingredient_id} name={self.name!r}>"
