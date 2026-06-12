"""Market-price routes (Enter/Update Market Prices use case).

Supports manual price entry, filtered time-series retrieval, and a
"latest price per ingredient at a location" helper used at formulation time.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Ingredient, MarketPrice, User
from app.schemas.market_price import MarketPriceCreate, MarketPriceRead

router = APIRouter(prefix="/market-prices", tags=["market-prices"])


@router.post("", response_model=MarketPriceRead, status_code=status.HTTP_201_CREATED)
async def create_price(
    payload: MarketPriceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MarketPrice:
    ingredient = await db.get(Ingredient, payload.ingredient_id)
    if ingredient is None:
        raise HTTPException(status_code=404, detail="Ingredient not found.")
    price = MarketPrice(
        ingredient_id=payload.ingredient_id,
        price_per_kg_rwf=payload.price_per_kg_rwf,
        price_date=payload.price_date,
        market_location=payload.market_location,
        entered_by_user_id=current_user.user_id,
    )
    db.add(price)
    await db.flush()
    await db.refresh(price)
    return price


@router.get("", response_model=list[MarketPriceRead])
async def list_prices(
    ingredient_id: int | None = Query(None),
    market_location: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    limit: int = Query(500, le=2000),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[MarketPrice]:
    stmt = select(MarketPrice)
    if ingredient_id is not None:
        stmt = stmt.where(MarketPrice.ingredient_id == ingredient_id)
    if market_location is not None:
        stmt = stmt.where(MarketPrice.market_location == market_location)
    if date_from is not None:
        stmt = stmt.where(MarketPrice.price_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(MarketPrice.price_date <= date_to)
    stmt = stmt.order_by(MarketPrice.price_date.desc()).limit(limit)
    return list(await db.scalars(stmt))


@router.get("/latest", response_model=list[MarketPriceRead])
async def latest_prices(
    market_location: str = Query(..., description="Market location to price from."),
    as_of: date | None = Query(None, description="Latest price on/before this date."),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[MarketPrice]:
    """Return the most recent price per ingredient at a given market."""
    cond = [MarketPrice.market_location == market_location]
    if as_of is not None:
        cond.append(MarketPrice.price_date <= as_of)

    # Latest price_date per ingredient at this location.
    subq = (
        select(
            MarketPrice.ingredient_id,
            func.max(MarketPrice.price_date).label("max_date"),
        )
        .where(*cond)
        .group_by(MarketPrice.ingredient_id)
        .subquery()
    )
    stmt = (
        select(MarketPrice)
        .join(
            subq,
            (MarketPrice.ingredient_id == subq.c.ingredient_id)
            & (MarketPrice.price_date == subq.c.max_date),
        )
        .where(MarketPrice.market_location == market_location)
    )
    return list(await db.scalars(stmt))
