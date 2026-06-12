"""Price-forecasting routes.

* POST /forecasts/refresh   train the model and (re)write forecasts.
* GET  /forecasts           current forecasts + recent history per ingredient.
* GET  /forecasts/backtest  walk-forward ML-vs-baseline evaluation metrics.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Ingredient, MarketPrice, User
from app.schemas.forecast import (
    BacktestResult,
    ForecastPoint,
    ForecastRefreshResult,
    IngredientForecast,
    MethodMetrics,
)
from app.services.forecasting import core, service

router = APIRouter(prefix="/forecasts", tags=["forecasts"])


async def _ingredient_names(db: AsyncSession) -> dict[int, str]:
    rows = list(await db.scalars(select(Ingredient)))
    return {i.ingredient_id: i.name for i in rows}


@router.post("/refresh", response_model=ForecastRefreshResult)
async def refresh_forecasts(
    horizon_months: int = Query(1, ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ForecastRefreshResult:
    forecasts = await service.generate_and_persist_forecasts(db, horizon=horizon_months)
    names = await _ingredient_names(db)
    items = [
        IngredientForecast(
            ingredient_id=ing_id,
            ingredient_name=names.get(ing_id, f"#{ing_id}"),
            model=core.MODEL_VERSION,
            forecast=[ForecastPoint(**p) for p in points],
        )
        for ing_id, points in forecasts.items()
    ]
    return ForecastRefreshResult(
        horizon_months=horizon_months,
        model=core.MODEL_VERSION,
        ingredients_forecast=len(items),
        forecasts=items,
    )


@router.get("", response_model=list[IngredientForecast])
async def list_forecasts(
    history_months: int = Query(12, ge=0, le=60),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[IngredientForecast]:
    names = await _ingredient_names(db)
    forecast_rows = list(
        await db.scalars(
            select(MarketPrice)
            .where(MarketPrice.is_forecast.is_(True))
            .order_by(MarketPrice.ingredient_id, MarketPrice.price_date)
        )
    )
    by_ing: dict[int, list[MarketPrice]] = {}
    for r in forecast_rows:
        by_ing.setdefault(r.ingredient_id, []).append(r)

    out: list[IngredientForecast] = []
    for ing_id, frows in by_ing.items():
        history: list[ForecastPoint] = []
        if history_months:
            hrows = list(
                await db.scalars(
                    select(MarketPrice)
                    .where(
                        MarketPrice.ingredient_id == ing_id,
                        MarketPrice.is_forecast.is_(False),
                    )
                    .order_by(MarketPrice.price_date.desc())
                    .limit(history_months)
                )
            )
            history = [
                ForecastPoint(date=h.price_date, price=h.price_per_kg_rwf,
                              lower=h.price_per_kg_rwf, upper=h.price_per_kg_rwf)
                for h in sorted(hrows, key=lambda x: x.price_date)
            ]
        out.append(IngredientForecast(
            ingredient_id=ing_id,
            ingredient_name=names.get(ing_id, f"#{ing_id}"),
            model=core.MODEL_VERSION,
            history=history,
            forecast=[
                ForecastPoint(date=r.price_date, price=r.price_per_kg_rwf,
                              lower=r.price_per_kg_rwf, upper=r.price_per_kg_rwf)
                for r in frows
            ],
        ))
    return out


@router.get("/backtest", response_model=BacktestResult)
async def backtest(
    test_months: int = Query(6, ge=2, le=12),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> BacktestResult:
    raw = await service.run_backtest(db, test_months=test_months)
    if "error" in raw:
        return BacktestResult(test_months=test_months, note=raw["error"])

    methods = [
        MethodMetrics(method=m["method"], n=m["n"], mae=m["mae"],
                      rmse=m["rmse"], mape=m["mape"])
        for key, m in raw.items()
        if key != "per_ingredient_ml" and m.get("n")
    ]
    per_ing = {
        str(ing): MethodMetrics(method=f"ingredient_{ing}", n=m["n"], mae=m["mae"],
                                rmse=m["rmse"], mape=m["mape"])
        for ing, m in raw.get("per_ingredient_ml", {}).items()
        if m.get("n")
    }
    return BacktestResult(test_months=test_months, methods=methods,
                          per_ingredient_ml=per_ing)
