"""Price-forecast I/O schemas."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class ForecastPoint(BaseModel):
    date: date
    price: float
    lower: float
    upper: float


class IngredientForecast(BaseModel):
    ingredient_id: int
    ingredient_name: str
    model: str
    history: list[ForecastPoint] = Field(default_factory=list)
    forecast: list[ForecastPoint] = Field(default_factory=list)


class ForecastRefreshResult(BaseModel):
    horizon_months: int
    model: str
    ingredients_forecast: int
    forecasts: list[IngredientForecast] = Field(default_factory=list)


class MethodMetrics(BaseModel):
    method: str
    n: int
    mae: float
    rmse: float
    mape: float


class BacktestResult(BaseModel):
    test_months: int
    methods: list[MethodMetrics] = Field(default_factory=list)
    per_ingredient_ml: dict[str, MethodMetrics] = Field(default_factory=dict)
    note: str | None = None


class FormulationBacktestMonth(BaseModel):
    date: date
    stale_cost_rwf: float
    forecast_cost_rwf: float
    savings_rwf: float
    savings_percent: float


class FormulationBacktestResult(BaseModel):
    test_months: int
    average_stale_cost_rwf: float
    average_forecast_cost_rwf: float
    average_savings_rwf: float
    savings_percent: float
    detailed_months: list[FormulationBacktestMonth]

