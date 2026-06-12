"""FastAPI application entrypoint.

Mounts the v1 API (auth, ingredients, market prices, flocks, formulations),
configures CORS, and exposes a health check.
OpenAPI/Swagger docs are auto-generated at /docs.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description=(
        "Multi-objective (NSGA-II) least-cost poultry feed formulation API "
        "for Sub-Saharan market conditions."
    ),
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# allow cross-origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.ENVIRONMENT}


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {"name": settings.PROJECT_NAME, "version": "0.1.0", "docs": "/docs", "redoc": "/redoc",}
