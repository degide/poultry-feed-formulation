"""Seed observed Rwanda price history into `market_prices`.

Loads the bundled monthly WFP-derived series (app/data/rwanda_price_history.csv)
and inserts one observed MarketPrice row per ingredient-month. Idempotent:
existing observed rows for the same ingredient/date/location are skipped, so it
is safe to re-run. Run after `seed_ingredients`.

Usage:
    python -m app.db.seed_price_history
"""
from __future__ import annotations

import asyncio
import csv
from datetime import date
from pathlib import Path

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models import Ingredient, MarketPrice

_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "rwanda_price_history.csv"


async def seed_price_history() -> None:
    if not _DATA_FILE.exists():
        raise FileNotFoundError(f"Price-history file not found: {_DATA_FILE}")

    with _DATA_FILE.open(newline="") as fh:
        rows = list(csv.DictReader(fh))

    async with AsyncSessionLocal() as db:
        # name -> ingredient_id
        ingredients = list(await db.scalars(select(Ingredient)))
        name_to_id = {ing.name: ing.ingredient_id for ing in ingredients}

        inserted = 0
        skipped = 0
        for row in rows:
            ing_id = name_to_id.get(row["ingredient_name"])
            if ing_id is None:
                continue
            d = date.fromisoformat(row["price_date"])
            loc = row["market_location"]
            exists = await db.scalar(
                select(MarketPrice.price_id).where(
                    MarketPrice.ingredient_id == ing_id,
                    MarketPrice.price_date == d,
                    MarketPrice.market_location == loc,
                    MarketPrice.is_forecast.is_(False),
                )
            )
            if exists is not None:
                skipped += 1
                continue
            db.add(MarketPrice(
                ingredient_id=ing_id,
                price_per_kg_rwf=float(row["price_per_kg_rwf"]),
                price_date=d,
                market_location=loc,
                is_forecast=False,
            ))
            inserted += 1
        await db.commit()
        print(f"Seeded price history: {inserted} inserted, {skipped} already present.")


if __name__ == "__main__":
    asyncio.run(seed_price_history())
