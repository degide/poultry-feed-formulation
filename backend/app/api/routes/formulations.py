"""Formulation routes.

Implements the Generate Formulation flow from the sequence diagram: the client
POSTs a request, receives a job id, polls the job endpoint, then renders the
Pareto front and selects a preferred formulation (which becomes the flock's
active ration). Also covers history viewing and PDF/CSV export.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models import (
    Flock,
    Formulation,
    FormulationIngredient,
    Ingredient,
    User,
)
from app.schemas.formulation import (
    FormulationDetail,
    FormulationIngredientDetail,
    FormulationMethodEnum,
    FormulationRead,
    FormulationRequest,
    JobAccepted,
    JobResult,
    JobState,
)
from app.services.export import formulation_to_csv, formulation_to_pdf
from app.services.formulation_runner import run_formulation_job
from app.services.jobs import job_store

router = APIRouter(prefix="/formulations", tags=["formulations"])


async def _owned_flock_or_404(db: AsyncSession, flock_id: int, user: User) -> Flock:
    flock = await db.get(Flock, flock_id)
    if flock is None or flock.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Flock not found.")
    return flock


async def _owned_formulation_or_404(
    db: AsyncSession, formulation_id: int, user: User
) -> Formulation:
    formulation = await db.scalar(
        select(Formulation)
        .where(Formulation.formulation_id == formulation_id)
        .options(selectinload(Formulation.ingredients))
    )
    if formulation is None:
        raise HTTPException(status_code=404, detail="Formulation not found.")
    flock = await db.get(Flock, formulation.flock_id)
    if flock is None or flock.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Formulation not found.")
    return formulation


async def _build_detail(db: AsyncSession, formulation: Formulation) -> FormulationDetail:
    ids = [fi.ingredient_id for fi in formulation.ingredients]
    names: dict[int, str] = {}
    if ids:
        rows = await db.scalars(
            select(Ingredient).where(Ingredient.ingredient_id.in_(ids))
        )
        names = {ing.ingredient_id: ing.name for ing in rows}
    items = [
        FormulationIngredientDetail(
            ingredient_id=fi.ingredient_id,
            ingredient_name=names.get(fi.ingredient_id, f"#{fi.ingredient_id}"),
            proportion_percent=fi.proportion_percent,
        )
        for fi in sorted(
            formulation.ingredients, key=lambda f: -f.proportion_percent
        )
    ]
    return FormulationDetail(
        formulation_id=formulation.formulation_id,
        flock_id=formulation.flock_id,
        generated_by=FormulationMethodEnum(formulation.generated_by.value),
        total_cost_per_kg_rwf=formulation.total_cost_per_kg_rwf,
        dtsi_score=formulation.dtsi_score,
        is_selected=formulation.is_selected,
        created_at=formulation.created_at,
        ingredients=items,
    )


@router.post("/generate", response_model=JobAccepted)
async def generate_formulation(
    payload: FormulationRequest,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobAccepted:
    await _owned_flock_or_404(db, payload.flock_id, current_user)

    job_id = uuid.uuid4().hex
    await job_store.create(job_id, payload.flock_id)

    background.add_task(
        run_formulation_job,
        job_id=job_id,
        flock_id=payload.flock_id,
        market_location=payload.market_location,
        method=payload.method,
        population_size=payload.population_size or settings.NSGA2_POPULATION_SIZE,
        max_generations=payload.max_generations or settings.NSGA2_MAX_GENERATIONS,
        price_mode=payload.price_mode.value,
        forecast_horizon_months=payload.forecast_horizon_months,
    )
    return JobAccepted(job_id=job_id, flock_id=payload.flock_id, state=JobState.pending)


@router.get("/jobs/{job_id}", response_model=JobResult)
async def get_job(
    job_id: str,
    _: User = Depends(get_current_user),
) -> JobResult:
    job = await job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job.to_result()


@router.get("/flocks/{flock_id}/history", response_model=list[FormulationRead])
async def formulation_history(
    flock_id: int,
    selected_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Formulation]:
    await _owned_flock_or_404(db, flock_id, current_user)
    stmt = (
        select(Formulation)
        .where(Formulation.flock_id == flock_id)
        .options(selectinload(Formulation.ingredients))
        .order_by(Formulation.created_at.desc())
    )
    if selected_only:
        stmt = stmt.where(Formulation.is_selected.is_(True))
    return list(await db.scalars(stmt))


@router.get("/{formulation_id}", response_model=FormulationDetail)
async def get_formulation(
    formulation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FormulationDetail:
    formulation = await _owned_formulation_or_404(db, formulation_id, current_user)
    return await _build_detail(db, formulation)


@router.post("/{formulation_id}/select", response_model=FormulationDetail)
async def select_formulation(
    formulation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FormulationDetail:
    """Mark a formulation as the flock's active ration (sequence diagram 12-14)."""
    formulation = await _owned_formulation_or_404(db, formulation_id, current_user)

    # Clear any previously selected formulation for this flock, then select this.
    await db.execute(
        update(Formulation)
        .where(Formulation.flock_id == formulation.flock_id)
        .values(is_selected=False)
    )
    formulation.is_selected = True
    flock = await db.get(Flock, formulation.flock_id)
    if flock is not None:
        flock.previous_formulation_id = formulation.formulation_id
    await db.flush()
    return await _build_detail(db, formulation)


@router.get("/{formulation_id}/export")
async def export_formulation(
    formulation_id: int,
    format: str = Query("pdf", pattern="^(pdf|csv)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    formulation = await _owned_formulation_or_404(db, formulation_id, current_user)
    detail = await _build_detail(db, formulation)

    if format == "csv":
        data = formulation_to_csv(detail)
        media_type = "text/csv"
        filename = f"formulation_{formulation_id}.csv"
    else:
        data = formulation_to_pdf(detail)
        media_type = "application/pdf"
        filename = f"formulation_{formulation_id}.pdf"

    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
