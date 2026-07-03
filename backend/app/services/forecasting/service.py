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

from sqlalchemy.orm import selectinload
from app.models import Ingredient, MarketPrice
from app.services.forecasting import core
from app.services.optimization.builder import build_problem
from app.services.optimization.lp import run_lp
from app.services.optimization.nutrition import constraints_for_flock

FORECAST_LOCATION = "Rwanda (forecast)"
# The coherent national monthly series the forecaster trains on. Ad-hoc manual
# price entries at individual markets are inputs for optimisation, not training
# data, so mixing them in would corrupt the series; we train on this location.
HISTORY_LOCATION = "Rwanda"


# Loading observed history
async def load_actual_panel(db: AsyncSession, market_location: str = "Rwanda") -> dict[int, list[tuple[date, float]]]:
    """Observed price observations grouped by ingredient for a specific market location."""
    rows = list(
        await db.scalars(
            select(MarketPrice)
            .where(
                MarketPrice.is_forecast.is_(False),
                MarketPrice.market_location == market_location,
            )
            .order_by(MarketPrice.ingredient_id, MarketPrice.price_date)
        )
    )
    panel: dict[int, list[tuple[date, float]]] = {}
    for r in rows:
        panel.setdefault(r.ingredient_id, []).append((r.price_date, r.price_per_kg_rwf))

    # Fallback to "Rwanda" (National Average) for any ingredient that has no history
    # or less than 12 points at this specific local market.
    if market_location != "Rwanda":
        national_rows = list(
            await db.scalars(
                select(MarketPrice)
                .where(
                    MarketPrice.is_forecast.is_(False),
                    MarketPrice.market_location == "Rwanda",
                )
                .order_by(MarketPrice.ingredient_id, MarketPrice.price_date)
            )
        )
        national_panel: dict[int, list[tuple[date, float]]] = {}
        for r in national_rows:
            national_panel.setdefault(r.ingredient_id, []).append((r.price_date, r.price_per_kg_rwf))
            
        for ing_id, nat_obs in national_panel.items():
            local_obs = panel.get(ing_id, [])
            if len(local_obs) < core.MIN_HISTORY_POINTS:
                panel[ing_id] = nat_obs

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

    # Find the global max date across all series
    global_max_date = None
    for series in panel.values():
        if not series.empty:
            m_date = series.index.max()
            if global_max_date is None or m_date > global_max_date:
                global_max_date = m_date

    results: dict[int, list[dict]] = {}
    for ing_id, series in panel.items():
        if len(series) < core.MIN_HISTORY_POINTS:
            continue
        # Skip stale series (e.g. Soybeans/Wheat which ended in 2015)
        if global_max_date is not None and (global_max_date - series.index.max()).days > 366:
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
    market_location: str = "Rwanda",
    horizon: int = 1,
) -> dict[int, list[dict]]:
    """Train, forecast `horizon` months, and persist forecasts as flagged rows.

    Uses an upsert (update existing forecast row for the same ingredient/date,
    else insert) rather than delete+insert, so forecast rows already referenced
    by a formulation's price snapshots are never orphaned.
    """
    
    obs_panel = await load_actual_panel(db, market_location=market_location)
    loop = asyncio.get_running_loop()
    forecasts = await loop.run_in_executor(None, _compute_forecasts, obs_panel, horizon)

    forecast_location = f"{market_location} (forecast)"

    for ing_id, points in forecasts.items():
        existing = {
            row.price_date: row
            for row in await db.scalars(
                select(MarketPrice).where(
                    MarketPrice.ingredient_id == ing_id,
                    MarketPrice.market_location == forecast_location,
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
                    market_location=forecast_location,
                    is_forecast=True,
                    forecast_model=core.MODEL_VERSION,
                ))
    await db.flush()
    return forecasts


async def ensure_forecasts(db: AsyncSession, market_location: str = "Rwanda", horizon: int = 1) -> None:
    """Generate forecasts if none are currently stored."""
    has_any = await db.scalar(
        select(MarketPrice.price_id)
        .where(
            MarketPrice.is_forecast.is_(True),
            MarketPrice.market_location == f"{market_location} (forecast)",
        )
        .limit(1)
    )
    if has_any is None:
        await generate_and_persist_forecasts(db, market_location=market_location, horizon=horizon)


async def latest_forecast_price_map(db: AsyncSession, market_location: str = "Rwanda") -> dict[int, float]:
    """Most recent forecast price per ingredient (for the optimiser)."""
    rows = list(
        await db.scalars(
            select(MarketPrice)
            .where(
                MarketPrice.is_forecast.is_(True),
                MarketPrice.market_location == f"{market_location} (forecast)",
            )
            .order_by(MarketPrice.ingredient_id, MarketPrice.price_date.desc())
        )
    )
    out: dict[int, float] = {}
    for r in rows:
        out.setdefault(r.ingredient_id, r.price_per_kg_rwf)  # first = latest
    return out


async def run_backtest(db: AsyncSession, market_location: str = "Rwanda", test_months: int = 6) -> dict:
    obs_panel = await load_actual_panel(db, market_location=market_location)
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _compute_backtest, obs_panel, test_months)


# Default manual prices for ingredients without WFP history during backtest
BACKTEST_MANUAL_PRICES = {
    "Soybean meal (44%)": 900.0,
    "Sunflower seed cake": 550.0,
    "Wheat bran": 300.0,
    "Limestone": 120.0,
    "Dicalcium phosphate": 1200.0,
    "Layer premix (vit/min)": 2500.0,
    "DL-Methionine": 6500.0,
}


async def run_formulation_backtest(
    db: AsyncSession,
    market_location: str = "Rwanda",
    test_months: int = 6,
) -> dict:
    """Run walk-forward feed formulation backtest.

    Compares realized costs when formulations are optimized against stale
    (latest observed) prices vs. forecasted prices, showing the out-of-sample
    feed cost savings.
    """
    ingredients = list(
        await db.scalars(
            select(Ingredient)
            .where(Ingredient.is_active.is_(True))
            .options(selectinload(Ingredient.nutritional_compositions))
        )
    )
    ingredient_dicts = [
        {
            "ingredient_id": ing.ingredient_id,
            "name": ing.name,
            "category": ing.category,
            "nutrients": {nc.nutrient_type: nc.value for nc in ing.nutritional_compositions},
        }
        for ing in ingredients
    ]

    constraints = constraints_for_flock("layer")

    obs_panel = await load_actual_panel(db, market_location=market_location)
    panel = _build_series_panel(obs_panel)
    if not panel:
        return {"error": "no price history found in DB"}

    longest = max(panel.values(), key=len)
    timeline = longest.index
    if len(timeline) <= core.MIN_HISTORY_POINTS + 1:
        return {"error": "insufficient history for formulation backtest"}

    start = max(core.MIN_HISTORY_POINTS, len(timeline) - test_months)
    
    total_stale_cost = 0.0
    total_forecast_cost = 0.0
    count = 0
    detailed_months = []

    for t in range(start, len(timeline)):
        prev_date = timeline[t - 1]
        target_date = timeline[t]

        # Train model on history up to prev_date
        train_panel = {
            i: s[s.index <= prev_date] for i, s in panel.items()
        }
        step_model = core.train_model(train_panel)
        if step_model is None:
            continue

        actual_t_minus_1 = {}
        actual_t = {}
        forecast_t = {}

        for ing in ingredient_dicts:
            ing_name = ing["name"]
            ing_id = ing["ingredient_id"]
            if ing_id in panel:
                series = panel[ing_id]
                hist_prev = series.loc[:prev_date]
                actual_t_minus_1[ing_id] = float(hist_prev.iloc[-1]) if not hist_prev.empty else BACKTEST_MANUAL_PRICES.get(ing_name, 0.0)
                
                hist_target = series.loc[:target_date]
                actual_t[ing_id] = float(hist_target.iloc[-1]) if not hist_target.empty else BACKTEST_MANUAL_PRICES.get(ing_name, 0.0)
                
                # Only forecast if the series is current (not stale in 2015)
                if series.index.max() >= prev_date:
                    hist_series = series[series.index <= prev_date]
                    fc = core.forecast_series(step_model, hist_series, ing_id, horizon=1)
                    forecast_t[ing_id] = float(fc[0][1]) if fc else actual_t_minus_1[ing_id]
                else:
                    forecast_t[ing_id] = actual_t_minus_1[ing_id]
            else:
                manual_p = BACKTEST_MANUAL_PRICES.get(ing_name, 0.0)
                actual_t_minus_1[ing_id] = manual_p
                actual_t[ing_id] = manual_p
                forecast_t[ing_id] = manual_p

        # Solve Latest Mode Formulation (using prices at t-1)
        prob_latest = build_problem(
            ingredients=ingredient_dicts,
            prices=actual_t_minus_1,
            constraints=constraints,
        )
        sol_latest = run_lp(prob_latest)

        # Solve Forecast Mode Formulation (using forecasted prices for t)
        prob_forecast = build_problem(
            ingredients=ingredient_dicts,
            prices=forecast_t,
            constraints=constraints,
        )
        sol_forecast = run_lp(prob_forecast)

        if sol_latest is None or not sol_latest.feasible:
            continue
        if sol_forecast is None or not sol_forecast.feasible:
            continue

        # Evaluate actual costs using actual prices at t
        actual_price_vec = np.array([actual_t[iid] for iid in prob_latest.ingredient_ids])
        cost_latest_actual = float(actual_price_vec @ sol_latest.proportions)
        cost_forecast_actual = float(actual_price_vec @ sol_forecast.proportions)

        savings = cost_latest_actual - cost_forecast_actual
        pct = (savings / cost_latest_actual) * 100.0 if cost_latest_actual > 0 else 0.0

        total_stale_cost += cost_latest_actual
        total_forecast_cost += cost_forecast_actual
        count += 1

        detailed_months.append({
            "date": target_date.date(),
            "stale_cost_rwf": round(cost_latest_actual, 2),
            "forecast_cost_rwf": round(cost_forecast_actual, 2),
            "savings_rwf": round(savings, 2),
            "savings_percent": round(pct, 2)
        })

    if count > 0:
        avg_stale = total_stale_cost / count
        avg_forecast = total_forecast_cost / count
        avg_savings = avg_stale - avg_forecast
        avg_pct = (avg_savings / avg_stale) * 100.0
        return {
            "test_months": count,
            "average_stale_cost_rwf": round(avg_stale, 2),
            "average_forecast_cost_rwf": round(avg_forecast, 2),
            "average_savings_rwf": round(avg_savings, 2),
            "savings_percent": round(avg_pct, 2),
            "detailed_months": detailed_months
        }
    return {"error": "no feasible formulations found during backtest"}
