"""Formulation, Pareto-front, and optimisation-job I/O schemas."""
from __future__ import annotations

import enum
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FormulationMethodEnum(str, enum.Enum):
    NSGA_II = "NSGA-II"
    LP = "LP"


class OptimisationMethod(str, enum.Enum):
    """Which engine(s) the client wants to run."""

    nsga2 = "nsga2"
    lp = "lp"
    both = "both"


class JobState(str, enum.Enum):
    pending = "pending"
    running = "running"
    complete = "complete"
    failed = "failed"


class PriceMode(str, enum.Enum):
    """Which prices feed the optimiser's cost objective."""

    latest = "latest"      # most recent observed market price
    forecast = "forecast"  # ML-predicted next-period price (dynamic mode)


class FormulationRequest(BaseModel):
    flock_id: int
    market_location: str = Field(
        description="Market whose latest prices to use, e.g. 'Kigali'."
    )
    method: OptimisationMethod = OptimisationMethod.both
    price_mode: PriceMode = PriceMode.latest
    forecast_horizon_months: int = Field(default=1, ge=1, le=12)
    # Optional overrides of the server defaults (Table 3.2).
    population_size: int | None = Field(default=None, ge=8, le=500)
    max_generations: int | None = Field(default=None, ge=10, le=2000)


class FormulationIngredientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ingredient_id: int
    proportion_percent: float


class FormulationIngredientDetail(BaseModel):
    ingredient_id: int
    ingredient_name: str
    proportion_percent: float


class FormulationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    formulation_id: int
    flock_id: int
    total_cost_per_kg_rwf: float
    dtsi_score: float
    is_selected: bool
    generated_by: FormulationMethodEnum
    created_at: datetime
    ingredients: list[FormulationIngredientRead] = Field(default_factory=list)


class FormulationDetail(BaseModel):
    """Rich, human-readable formulation with ingredient names + benchmark metrics."""

    formulation_id: int
    flock_id: int
    generated_by: FormulationMethodEnum
    total_cost_per_kg_rwf: float
    dtsi_score: float
    cosine_distance: float | None = None
    is_selected: bool
    created_at: datetime
    ingredients: list[FormulationIngredientDetail]


class ParetoPoint(BaseModel):
    """One solution on the Pareto front, ready for scatter-plot rendering."""

    formulation_id: int
    total_cost_per_kg_rwf: float
    dtsi_score: float
    cosine_distance: float
    generated_by: FormulationMethodEnum
    proportions: dict[str, float]  # ingredient_name -> percent


class JobAccepted(BaseModel):
    job_id: str
    flock_id: int
    state: JobState
    message: str = "Optimisation job accepted."


class JobResult(BaseModel):
    job_id: str
    flock_id: int
    state: JobState
    error: str | None = None
    nsga2_front: list[ParetoPoint] = Field(default_factory=list)
    lp_solution: ParetoPoint | None = None
