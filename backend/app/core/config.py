"""Application configuration.

Loads settings from environment variables (and a local .env file in
development) using pydantic-settings. Centralising configuration here keeps
secrets out of source control and makes the FastAPI/SQLAlchemy/Alembic stack
read from a single source of truth.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field, PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Project metadata ---
    PROJECT_NAME: str = "Poultry Feed Formulation Platform"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"  # development | production

    # --- PostgreSQL connection ---
    POSTGRES_USER: str = "feed_user"
    POSTGRES_PASSWORD: str = "feed_password"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "feed_formulation"

    # --- JWT / security ---
    # Generate a strong key for production, e.g. `openssl rand -hex 32`
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_use_openssl_rand_hex_32"
    ALGORITHM: str = "HS256"
    # Token expiry of 24h.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # --- NSGA-II default parameters (server-side) ---
    NSGA2_POPULATION_SIZE: int = 150
    NSGA2_MAX_GENERATIONS: int = 500
    NSGA2_CROSSOVER_PROB: float = 0.9
    NSGA2_SBX_ETA: float = 20.0
    NSGA2_MUTATION_ETA: float = 20.0
    NSGA2_PENALTY_COEFFICIENT: float = 1_000_000.0  # 10^6

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        """Async SQLAlchemy URL (asyncpg driver)."""
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                path=self.POSTGRES_DB,
            )
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SYNC_DATABASE_URL(self) -> str:
        """Synchronous URL (psycopg) used by Alembic migrations."""
        return str(
            PostgresDsn.build(
                scheme="postgresql+psycopg",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                path=self.POSTGRES_DB,
            )
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
