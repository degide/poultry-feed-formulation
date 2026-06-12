"""Flock profile I/O schemas."""
from __future__ import annotations

import enum

from pydantic import BaseModel, ConfigDict, Field


class FlockType(str, enum.Enum):
    broiler = "broiler"
    layer = "layer"


class FlockBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    type: FlockType
    current_age_weeks: int = Field(ge=0)
    flock_size: int = Field(gt=0)


class FlockCreate(FlockBase):
    pass


class FlockUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    type: FlockType | None = None
    current_age_weeks: int | None = Field(default=None, ge=0)
    flock_size: int | None = Field(default=None, gt=0)


class FlockRead(FlockBase):
    model_config = ConfigDict(from_attributes=True)

    flock_id: int
    user_id: int
    previous_formulation_id: int | None = None
