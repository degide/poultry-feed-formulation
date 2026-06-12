"""Ingredient routes (CRUD + nutritional profiles).

Reads are available to any authenticated user (View Ingredient Database use
case); writes are restricted to administrators (Manage Ingredient Database).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models import Ingredient, NutritionalComposition, User
from app.schemas.ingredient import (
    IngredientCreate,
    IngredientRead,
    IngredientUpdate,
)

router = APIRouter(prefix="/ingredients", tags=["ingredients"])


async def _get_or_404(db: AsyncSession, ingredient_id: int) -> Ingredient:
    ingredient = await db.scalar(
        select(Ingredient)
        .where(Ingredient.ingredient_id == ingredient_id)
        .options(selectinload(Ingredient.nutritional_compositions))
    )
    if ingredient is None:
        raise HTTPException(status_code=404, detail="Ingredient not found.")
    return ingredient


@router.get("", response_model=list[IngredientRead])
async def list_ingredients(
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Ingredient]:
    stmt = select(Ingredient).options(
        selectinload(Ingredient.nutritional_compositions)
    )
    if active_only:
        stmt = stmt.where(Ingredient.is_active.is_(True))
    result = await db.scalars(stmt.order_by(Ingredient.ingredient_id))
    return list(result)


@router.get("/{ingredient_id}", response_model=IngredientRead)
async def get_ingredient(
    ingredient_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Ingredient:
    return await _get_or_404(db, ingredient_id)


@router.post("", response_model=IngredientRead, status_code=status.HTTP_201_CREATED)
async def create_ingredient(
    payload: IngredientCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> Ingredient:
    ingredient = Ingredient(
        name=payload.name, category=payload.category, is_active=payload.is_active
    )
    for nut in payload.nutrients:
        ingredient.nutritional_compositions.append(
            NutritionalComposition(
                nutrient_type=nut.nutrient_type,
                value=nut.value,
                unit=nut.unit,
                source=nut.source,
                analysis_date=nut.analysis_date,
            )
        )
    db.add(ingredient)
    await db.flush()
    return await _get_or_404(db, ingredient.ingredient_id)


@router.patch("/{ingredient_id}", response_model=IngredientRead)
async def update_ingredient(
    ingredient_id: int,
    payload: IngredientUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> Ingredient:
    ingredient = await _get_or_404(db, ingredient_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ingredient, field, value)
    await db.flush()
    return ingredient
