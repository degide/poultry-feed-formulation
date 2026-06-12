"""Aggregate API v1 router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    auth,
    flocks,
    forecasts,
    formulations,
    ingredients,
    market_prices,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(ingredients.router)
api_router.include_router(market_prices.router)
api_router.include_router(flocks.router)
api_router.include_router(forecasts.router)
api_router.include_router(formulations.router)
