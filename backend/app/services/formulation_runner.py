"""Formulation job orchestration.

Builds the optimisation problem from current database state, runs the LP
baseline and/or NSGA-II off the event loop (thread executor), persists every
resulting formulation (so history and aggregate stats work), and records the
Pareto front in the job store for the polling client.
"""

from __future__ import annotations

import asyncio

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models import (
    Flock,
    Formulation,
    FormulationIngredient,
    FormulationMethod,
    FormulationPriceSnapshot,
    Ingredient,
    MarketPrice,
)
from app.schemas.formulation import (
    FormulationMethodEnum,
    JobState,
    OptimisationMethod,
    ParetoPoint,
)
from app.services.jobs import job_store
from app.services.optimization.builder import build_problem
from app.services.optimization.lp import run_lp
from app.services.optimization.metrics import cosine_distance
from app.services.optimization.nsga2 import run_nsga2
from app.services.optimization.nutrition import constraints_for_flock
from app.services.optimization.problem import FeedFormulationProblem
from app.services.optimization.solution import Solution

# Ingredients with proportion below this (fraction) are omitted when persisting.
_MIN_STORED_FRACTION = 5e-5


async def _load_inputs(db: AsyncSession, flock: Flock, market_location: str):
    """Fetch active ingredients (+nutrients), latest prices, previous ration."""
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

    # Latest price per ingredient at the requested market.
    price_rows = list(
        await db.scalars(
            select(MarketPrice)
            .where(MarketPrice.market_location == market_location)
            .order_by(MarketPrice.ingredient_id, MarketPrice.price_date.desc())
        )
    )
    prices: dict[int, float] = {}
    price_ids: dict[int, int] = {}
    for row in price_rows:
        if row.ingredient_id not in prices:  # first = latest (ordered desc)
            prices[row.ingredient_id] = row.price_per_kg_rwf
            price_ids[row.ingredient_id] = row.price_id

    # Previous validated ration as fractions.
    previous: dict[int, float] | None = None
    if flock.previous_formulation_id is not None:
        prev_rows = list(
            await db.scalars(
                select(FormulationIngredient).where(
                    FormulationIngredient.formulation_id
                    == flock.previous_formulation_id
                )
            )
        )
        if prev_rows:
            previous = {r.ingredient_id: r.proportion_percent / 100.0 for r in prev_rows}

    return ingredient_dicts, prices, price_ids, previous


async def _apply_forecast_overrides(
    db: AsyncSession,
    prices: dict[int, float],
    price_ids: dict[int, int],
    horizon: int,
    market_location: str,
) -> list[int]:
    """Override observed prices with the ML forecast where available.

    Ensures forecasts exist, then for each forecastable ingredient replaces the
    cost coefficient (and the linked price row used for snapshots) with the
    next-period forecast row (earliest forecast month). Ingredients without a
    forecast (e.g. imported inputs) keep their observed/manual price. Returns
    the list of overridden ids.
    """
    from app.services.forecasting import service as forecast_service

    await forecast_service.ensure_forecasts(db, market_location=market_location, horizon=horizon)
    forecast_rows = list(
        await db.scalars(
            select(MarketPrice)
            .where(
                MarketPrice.is_forecast.is_(True),
                MarketPrice.market_location == f"{market_location} (forecast)",
            )
            .order_by(MarketPrice.ingredient_id, MarketPrice.price_date.asc())
        )
    )
    overridden: list[int] = []
    seen: set[int] = set()
    for row in forecast_rows:
        if row.ingredient_id in seen:  # keep only the earliest (next period)
            continue
        seen.add(row.ingredient_id)
        prices[row.ingredient_id] = row.price_per_kg_rwf
        price_ids[row.ingredient_id] = row.price_id
        overridden.append(row.ingredient_id)
    return overridden


def _solve(
    problem: FeedFormulationProblem,
    method: OptimisationMethod,
    pop_size: int,
    max_gen: int,
) -> tuple[list[Solution], Solution | None]:
    """CPU-bound solve step (run inside a thread executor)."""
    nsga_front: list[Solution] = []
    lp_solution: Solution | None = None
    if method in (OptimisationMethod.lp, OptimisationMethod.both):
        lp_solution = run_lp(problem)
        if (
            method == OptimisationMethod.both
            and problem.previous_formulation is None
            and lp_solution is not None
            and lp_solution.feasible
        ):
            problem.previous_formulation = lp_solution.proportions.copy()
    if method in (OptimisationMethod.nsga2, OptimisationMethod.both):
        nsga_front = run_nsga2(
            problem,
            population_size=pop_size,
            max_generations=max_gen,
            crossover_prob=settings.NSGA2_CROSSOVER_PROB,
            sbx_eta=settings.NSGA2_SBX_ETA,
            mutation_eta=settings.NSGA2_MUTATION_ETA,
        )
    return nsga_front, lp_solution


async def _persist(
    db: AsyncSession,
    flock_id: int,
    problem: FeedFormulationProblem,
    solution: Solution,
    method: FormulationMethod,
    price_ids: dict[int, int],
) -> Formulation:
    formulation = Formulation(
        flock_id=flock_id,
        total_cost_per_kg_rwf=solution.cost,
        dtsi_score=solution.dtsi,
        is_selected=False,
        generated_by=method,
    )
    for ingredient_id, frac in zip(problem.ingredient_ids, solution.proportions):
        if frac < _MIN_STORED_FRACTION:
            continue
        formulation.ingredients.append(
            FormulationIngredient(
                ingredient_id=ingredient_id,
                proportion_percent=float(frac * 100.0),
            )
        )
    for pid in price_ids.values():
        formulation.price_snapshots.append(
            FormulationPriceSnapshot(price_id=pid)
        )
    db.add(formulation)
    await db.flush()
    return formulation


def _to_point(
    problem: FeedFormulationProblem,
    solution: Solution,
    formulation_id: int,
    method: FormulationMethodEnum,
) -> ParetoPoint:
    cos = (
        cosine_distance(solution.proportions, problem.previous_formulation)
        if problem.previous_formulation is not None
        else 0.0
    )
    proportions = {
        name: round(float(frac * 100.0), 4)
        for name, frac in zip(problem.ingredient_names, solution.proportions)
        if frac >= _MIN_STORED_FRACTION
    }
    return ParetoPoint(
        formulation_id=formulation_id,
        total_cost_per_kg_rwf=round(solution.cost, 2),
        dtsi_score=round(solution.dtsi, 6),
        cosine_distance=round(cos, 6),
        generated_by=method,
        proportions=proportions,
    )


async def run_formulation_job(
    job_id: str,
    flock_id: int,
    market_location: str,
    method: OptimisationMethod,
    population_size: int,
    max_generations: int,
    price_mode: str = "latest",
    forecast_horizon_months: int = 1,
) -> None:
    await job_store.update(job_id, state=JobState.running)
    try:
        async with AsyncSessionLocal() as db:
            flock = await db.get(Flock, flock_id)
            if flock is None:
                raise ValueError("Flock not found.")

            ingredient_dicts, prices, price_ids, previous = await _load_inputs(
                db, flock, market_location
            )

            # Dynamic mode: replace observed prices with ML forecasts where we
            # have a trained series (domestically-traded ingredients).
            if price_mode == "forecast":
                await _apply_forecast_overrides(
                    db, prices, price_ids, forecast_horizon_months, market_location
                )

            problem = build_problem(
                ingredients=ingredient_dicts,
                prices=prices,
                constraints=constraints_for_flock(flock.type),
                previous_formulation=previous,
                penalty_coefficient=settings.NSGA2_PENALTY_COEFFICIENT,
            )

            loop = asyncio.get_running_loop()
            nsga_front, lp_solution = await loop.run_in_executor(
                None, _solve, problem, method, population_size, max_generations
            )

            nsga_points: list[ParetoPoint] = []
            for sol in nsga_front:
                formulation = await _persist(
                    db, flock_id, problem, sol, FormulationMethod.NSGA_II, price_ids
                )
                nsga_points.append(
                    _to_point(problem, sol, formulation.formulation_id, FormulationMethodEnum.NSGA_II)
                )

            lp_point: ParetoPoint | None = None
            if lp_solution is not None and lp_solution.feasible:
                formulation = await _persist(
                    db, flock_id, problem, lp_solution, FormulationMethod.LP, price_ids
                )
                lp_point = _to_point(
                    problem, lp_solution, formulation.formulation_id, FormulationMethodEnum.LP
                )

            await db.commit()

        await job_store.update(
            job_id,
            state=JobState.complete,
            nsga2_front=nsga_points,
            lp_solution=lp_point,
        )
    except Exception as exc:  # noqa: BLE001 - surface any failure to the client
        await job_store.update(job_id, state=JobState.failed, error=str(exc))
