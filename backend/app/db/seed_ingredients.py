"""Seed the validated 12-ingredient library.

Run after migrations:

    python -m app.db.seed_ingredients

The script is idempotent: ingredients are matched by name, so re-running it
will not create duplicates. Nutrient values are sourced from MINAGRI (2021) and
NRC (1994); `source` and an analysis date are recorded
on each nutrient row to support the data-quality flag.
"""
from __future__ import annotations

import asyncio
from datetime import date

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models import Ingredient, NutritionalComposition

# Nutrient column order: CP%, ME kcal/kg, Lys %CP, Met %CP, Ca%, P av%, CF%, DM%
NUTRIENT_SPECS: list[tuple[str, str]] = [
    ("crude_protein", "%"),
    ("metabolisable_energy", "kcal/kg"),
    ("lysine", "%CP"),
    ("methionine", "%CP"),
    ("calcium", "%"),
    ("available_phosphorus", "%"),
    ("crude_fibre", "%"),
    ("dry_matter", "%"),
]

# (name, category, [CP, ME, Lys, Met, Ca, Pav, CF, DM])
INGREDIENT_LIBRARY: list[tuple[str, str, list[float]]] = [
    ("Whole maize grain",      "energy_source",  [9.0,  3350, 2.5, 1.8,  0.02, 0.10, 2.2,  88]),
    ("Soybean meal (44%)",     "protein_source", [44.0, 2240, 6.1, 1.4,  0.35, 0.25, 7.0,  89]),
    ("Sunflower seed cake",    "protein_source", [28.0, 1900, 3.2, 1.9,  0.40, 0.30, 22.0, 90]),
    ("Fishmeal (65% CP)",      "protein_source", [65.0, 2880, 5.0, 2.8,  5.50, 2.80, 1.0,  92]),
    ("Wheat bran",             "energy_source",  [15.5, 1500, 3.4, 1.5,  0.13, 0.15, 10.0, 88]),
    ("Cassava meal",           "energy_source",  [2.5,  3200, 1.5, 0.7,  0.10, 0.05, 3.5,  86]),
    ("Limestone",              "mineral",        [0.0,  0,    0.0, 0.0,  38.0, 0.00, 0.0,  100]),
    ("Dicalcium phosphate",    "mineral",        [0.0,  0,    0.0, 0.0,  22.0, 18.0, 0.0,  100]),
    ("Sodium chloride (salt)", "mineral",        [0.0,  0,    0.0, 0.0,  0.0,  0.00, 0.0,  100]),
    ("Layer premix (vit/min)", "premix",         [0.0,  0,    0.0, 0.0,  0.0,  0.00, 0.0,  100]),
    ("Crude palm oil",         "fat",            [0.0,  8800, 0.0, 0.0,  0.0,  0.00, 0.0,  100]),
    ("DL-Methionine",          "additive",       [58.0, 3500, 0.0, 100.0, 0.0, 0.00, 0.0,  100]),
]

SOURCE = "MINAGRI (2021); NRC (1994)"
ANALYSIS_DATE = date(2025, 1, 1)


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        for name, category, values in INGREDIENT_LIBRARY:
            existing = await session.scalar(
                select(Ingredient).where(Ingredient.name == name)
            )
            if existing is not None:
                print(f"  = skip (exists): {name}")
                continue

            ingredient = Ingredient(name=name, category=category, is_active=True)
            for (nutrient_type, unit), value in zip(NUTRIENT_SPECS, values):
                ingredient.nutritional_compositions.append(
                    NutritionalComposition(
                        nutrient_type=nutrient_type,
                        value=float(value),
                        unit=unit,
                        source=SOURCE,
                        analysis_date=ANALYSIS_DATE,
                    )
                )
            session.add(ingredient)
            print(f"  + added: {name} ({category})")

        await session.commit()
    print("Ingredient library seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
