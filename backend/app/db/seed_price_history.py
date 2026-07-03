"""Seed observed Rwanda price history into `market_prices`.

Loads the WFP dataset (app/data/wfp_food_prices_rwa.csv), aggregates price series
for both the national average ("Rwanda") and each specific market location
(formatted as "Province / District / Market"), and seeds them.

Usage:
    python -m app.db.seed_price_history
"""
from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path

import pandas as pd
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models import Ingredient, MarketPrice

_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "wfp_food_prices_rwa.csv"
PALM_OIL_DENSITY = 0.91

COMMODITY_MAPPING = {
    "Maize": "Whole maize grain",
    "Cassava": "Cassava meal",
    "Salt": "Sodium chloride (salt)",
    "Oil (palm)": "Crude palm oil",
    "Fish (dry)": "Fishmeal (65% CP)",
    "Soybeans": "Soybean meal (44%)",
    "Wheat": "Wheat bran"
}


async def seed_price_history() -> None:
    if not _DATA_FILE.exists():
        raise FileNotFoundError(f"Price-history file not found: {_DATA_FILE}")

    print("Loading and preparing WFP food prices...")
    df = pd.read_csv(_DATA_FILE)
    df['date'] = pd.to_datetime(df['date'])

    # Filter relevant rows
    df_filtered = df[df['commodity'].isin(COMMODITY_MAPPING.keys())].copy()
    
    # 1. National average aggregation
    print("Aggregating national average prices...")
    grouped_national = df_filtered.groupby(['date', 'commodity'])['price'].mean().reset_index()
    grouped_national['market_location'] = "Rwanda"

    # 2. Local market aggregation (Province / District / Market)
    print("Aggregating specific market prices...")
    df_clean = df_filtered.dropna(subset=['admin1', 'admin2', 'market'])
    grouped_market = df_clean.groupby(['date', 'commodity', 'market', 'admin1', 'admin2'])['price'].mean().reset_index()
    grouped_market['market_location'] = (
        grouped_market['admin1'].astype(str) + " / " + 
        grouped_market['admin2'].astype(str) + " / " + 
        grouped_market['market'].astype(str)
    )

    # Combine both datasets
    to_insert_df = pd.concat([
        grouped_national[['date', 'commodity', 'price', 'market_location']],
        grouped_market[['date', 'commodity', 'price', 'market_location']]
    ], ignore_index=True)

    async with AsyncSessionLocal() as db:
        # Load ingredients to map name -> ingredient_id
        ingredients = list(await db.scalars(select(Ingredient)))
        name_to_id = {ing.name: ing.ingredient_id for ing in ingredients}

        # Load existing price keys to optimize idempotency checks
        print("Fetching existing price records from DB...")
        existing_rows = list(await db.execute(
            select(MarketPrice.ingredient_id, MarketPrice.price_date, MarketPrice.market_location)
            .where(MarketPrice.is_forecast.is_(False))
        ))
        # Set of tuples: (ingredient_id, price_date, market_location)
        existing_keys = {(r[0], r[1], r[2]) for r in existing_rows}

        inserted = 0
        skipped = 0
        
        print("Inserting price history records...")
        for _, row in to_insert_df.iterrows():
            ing_name = COMMODITY_MAPPING[row['commodity']]
            ing_id = name_to_id.get(ing_name)
            if ing_id is None:
                continue

            d = row['date'].date()
            loc = row['market_location']
            
            # Check idempotency in memory
            if (ing_id, d, loc) in existing_keys:
                skipped += 1
                continue

            price = float(row['price'])
            # Convert palm oil from liters to kilograms
            if ing_name == "Crude palm oil":
                price = price / PALM_OIL_DENSITY

            db.add(MarketPrice(
                ingredient_id=ing_id,
                price_per_kg_rwf=price,
                price_date=d,
                market_location=loc,
                is_forecast=False,
            ))
            # Track key to avoid duplicate insertions within the same run
            existing_keys.add((ing_id, d, loc))
            inserted += 1

            if inserted % 2000 == 0 and inserted > 0:
                await db.flush()

        await db.commit()
        print(f"Seeding complete: {inserted} inserted, {skipped} skipped.")


if __name__ == "__main__":
    asyncio.run(seed_price_history())
