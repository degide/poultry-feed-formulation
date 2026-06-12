"""User and token I/O schemas."""
from __future__ import annotations

import enum
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(str, enum.Enum):
    farmer = "farmer"
    feed_manager = "feed_manager"
    admin = "admin"


class UserBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    role: UserRole = UserRole.farmer


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: int | None = None
