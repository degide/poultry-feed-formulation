"""Forecasting service: bridges the ML core to the database and the API.

Loads observed price history from `market_prices`, trains the pooled model off
the event loop, writes forecasts back as `is_forecast=True` rows (so they are
first-class prices the optimiser and snapshots can consume), and exposes the
walk-forward backtest used for the dissertation's evaluation chapter.
"""

from __future__ import annotations

import asyncio
from datetime import date

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MarketPrice
from app.services.forecasting import core

FORECAST_LOCATION = "Rwanda (forecast)"
# The coherent national monthly series the forecaster trains on. Ad-hoc manual
# price entries at individual markets are inputs for optimisation, not training
# data, so mixing them in would corrupt the series; we train on this location.
HISTORY_LOCATION = "Rwanda"


# Loading observed history
async def load_actual_panel(db: AsyncSession) -> dict[int, list[tuple[date, float]]]:
    """Observed national-series price observations grouped by ingredient."""
    rows = list(
        await db.scalars(
            select(MarketPrice)
            .where(
                MarketPrice.is_forecast.is_(False),
                MarketPrice.market_location == HISTORY_LOCATION,
            )
            .order_by(MarketPrice.ingredient_id, MarketPrice.price_date)
        )
    )
    panel: dict[int, list[tuple[date, float]]] = {}
    for r in rows:
        panel.setdefault(r.ingredient_id, []).append((r.price_date, r.price_per_kg_rwf))
    return panel


def _build_series_panel(
    obs_panel: dict[int, list[tuple[date, float]]]
) -> dict[int, pd.Series]:
    return {
        ing_id: core.to_monthly_series(obs)
        for ing_id, obs in obs_panel.items()
    }


# Sync compute steps (run in a thread executor)
def _compute_forecasts(
    obs_panel: dict[int, list[tuple[date, float]]],
    horizon: int,
) -> dict[int, list[dict]]:
    panel = _build_series_panel(obs_panel)
    model = core.train_model(panel)
    if model is None:
        return {}

    results: dict[int, list[dict]] = {}
    for ing_id, series in panel.items():
        if len(series) < core.MIN_HISTORY_POINTS:
            continue
        fc = core.forecast_series(model, series, ing_id, horizon=horizon)
        if not fc:
            continue
        # 80% prediction interval from recent return volatility.
        rets = np.log(series / series.shift(1)).dropna()
        sigma = float(rets.tail(6).std()) if len(rets) >= 2 else 0.0
        points = []
        for step, (d, price) in enumerate(fc, start=1):
            band = price * (np.exp(1.2816 * sigma * np.sqrt(step)) - 1.0)
            points.append({
                "date": d.date(),
                "price": round(price, 2),
                "lower": round(max(0.0, price - band), 2),
                "upper": round(price + band, 2),
            })
        results[ing_id] = points
    return results


def _compute_backtest(
    obs_panel: dict[int, list[tuple[date, float]]],
    test_months: int,
) -> dict:
    panel = _build_series_panel(obs_panel)
    return core.walk_forward_backtest(panel, test_months=test_months)


# Public async API
async def generate_and_persist_forecasts(
    db: AsyncSession,
    horizon: int = 1,
) -> dict[int, list[dict]]:
    """Train, forecast `horizon` months, and persist forecasts as flagged rows.

    Uses an upsert (update existing forecast row for the same ingredient/date,
    else insert) rather than delete+insert, so forecast rows already referenced
    by a formulation's price snapshots are never orphaned.
    """
    
    obs_panel = await load_actual_panel(db)
    loop = asyncio.get_running_loop()
    forecasts = await loop.run_in_executor(None, _compute_forecasts, obs_panel, horizon)

    for ing_id, points in forecasts.items():
        existing = {
            row.price_date: row
            for row in await db.scalars(
                select(MarketPrice).where(
                    MarketPrice.ingredient_id == ing_id,
                    MarketPrice.is_forecast.is_(True),
                )
            )
        }
        for pt in points:
            row = existing.get(pt["date"])
            if row is not None:  # update in place
                row.price_per_kg_rwf = pt["price"]
                row.forecast_model = core.MODEL_VERSION
            else:
                db.add(MarketPrice(
                    ingredient_id=ing_id,
                    price_per_kg_rwf=pt["price"],
                    price_date=pt["date"],
                    market_location=FORECAST_LOCATION,
                    is_forecast=True,
                    forecast_model=core.MODEL_VERSION,
                ))
    await db.flush()
    return forecasts


async def ensure_forecasts(db: AsyncSession, horizon: int = 1) -> None:
    """Generate forecasts if none are currently stored."""
    has_any = await db.scalar(
        select(MarketPrice.price_id).where(MarketPrice.is_forecast.is_(True)).limit(1)
    )
    if has_any is None:
        await generate_and_persist_forecasts(db, horizon=horizon)


async def latest_forecast_price_map(db: AsyncSession) -> dict[int, float]:
    """Most recent forecast price per ingredient (for the optimiser)."""
    rows = list(
        await db.scalars(
            select(MarketPrice)
            .where(MarketPrice.is_forecast.is_(True))
            .order_by(MarketPrice.ingredient_id, MarketPrice.price_date.desc())
        )
    )
    out: dict[int, float] = {}
    for r in rows:
        out.setdefault(r.ingredient_id, r.price_per_kg_rwf)  # first = latest
    return out


async def run_backtest(db: AsyncSession, test_months: int = 6) -> dict:
    obs_panel = await load_actual_panel(db)
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _compute_backtest, obs_panel, test_months)
