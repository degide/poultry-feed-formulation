"""Ingredient and nutritional-composition I/O schemas."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class NutrientValueBase(BaseModel):
    nutrient_type: str = Field(max_length=60)
    value: float
    unit: str = Field(max_length=20)
    source: str | None = None
    analysis_date: date | None = None


class NutrientValueRead(NutrientValueBase):
    model_config = ConfigDict(from_attributes=True)

    comp_id: int


class IngredientBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(max_length=60)
    is_active: bool = True


class IngredientCreate(IngredientBase):
    nutrients: list[NutrientValueBase] = Field(default_factory=list)


class IngredientUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    category: str | None = Field(default=None, max_length=60)
    is_active: bool | None = None


class IngredientRead(IngredientBase):
    model_config = ConfigDict(from_attributes=True)

    ingredient_id: int
    nutritional_compositions: list[NutrientValueRead] = Field(default_factory=list)
