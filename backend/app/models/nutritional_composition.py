"""Nutritional composition model.

Corresponds to `nutritional_compositions`. Each row records one nutrient value
for one ingredient (e.g. crude protein = 44.0 % for soybean meal). Storing
nutrients as rows rather than fixed columns keeps the schema flexible for
different species/production systems and lets each value carry
its own source citation and `analysis_date` for the data-quality flag.
"""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.ingredient import Ingredient


class NutritionalComposition(Base):
    __tablename__ = "nutritional_compositions"

    comp_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.ingredient_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # crude_protein | metabolisable_energy | lysine | methionine | calcium |
    # available_phosphorus | crude_fibre | dry_matter ...
    nutrient_type: Mapped[str] = mapped_column(String(60), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)  # %, kcal/kg, %CP
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    analysis_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    ingredient: Mapped["Ingredient"] = relationship(
        back_populates="nutritional_compositions"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<NutritionalComposition ingredient_id={self.ingredient_id} "
            f"{self.nutrient_type}={self.value}{self.unit}>"
        )
