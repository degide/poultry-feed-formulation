"""Market price model (time-series).

Corresponds to `market_prices`. Holds one wholesale price observation for an
ingredient at a given market location on a given date. The
composite index on (ingredient_id, price_date) supports the time-series queries
used to build the 12-week benchmark dataset and to fetch the latest price per
ingredient at formulation time.
"""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.formulation import FormulationPriceSnapshot
    from app.models.ingredient import Ingredient
    from app.models.user import User


class MarketPrice(Base, TimestampMixin):
    __tablename__ = "market_prices"
    __table_args__ = (
        Index("ix_market_prices_ingredient_date", "ingredient_id", "price_date"),
        Index("ix_market_prices_forecast", "ingredient_id", "is_forecast"),
    )

    price_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.ingredient_id", ondelete="CASCADE"),
        nullable=False,
    )
    price_per_kg_rwf: Mapped[float] = mapped_column(Float, nullable=False)
    price_date: Mapped[date] = mapped_column(Date, nullable=False)
    market_location: Mapped[str] = mapped_column(String(80), nullable=False)
    entered_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )
    # True when this row is a model-generated forecast rather than an observed
    # price; `forecast_model` records which forecaster produced it (provenance).
    is_forecast: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    forecast_model: Mapped[str | None] = mapped_column(String(60), nullable=True)

    # Relationships
    ingredient: Mapped["Ingredient"] = relationship(back_populates="market_prices")
    entered_by: Mapped["User | None"] = relationship(back_populates="submitted_prices")
    snapshot_links: Mapped[list["FormulationPriceSnapshot"]] = relationship(
        back_populates="market_price",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<MarketPrice ingredient_id={self.ingredient_id} "
            f"{self.price_per_kg_rwf} RWF/kg @ {self.market_location} {self.price_date}>"
        )
