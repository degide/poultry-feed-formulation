"""Market-price I/O schemas (time-series)."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class MarketPriceBase(BaseModel):
    ingredient_id: int
    price_per_kg_rwf: float = Field(gt=0)
    price_date: date
    market_location: str = Field(max_length=80)


class MarketPriceCreate(MarketPriceBase):
    pass


class MarketPriceRead(MarketPriceBase):
    model_config = ConfigDict(from_attributes=True)

    price_id: int
    entered_by_user_id: int | None = None
    created_at: datetime
