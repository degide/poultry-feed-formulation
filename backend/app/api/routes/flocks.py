"""Flock-profile routes (Configure / Manage Flock Profiles use cases).

Users only see and manage their own flocks. Feed managers may own several
flocks (Manage Multiple Flock Profiles); this is naturally supported since
flocks are scoped by `user_id`.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Flock, User
from app.schemas.flock import FlockCreate, FlockRead, FlockUpdate

router = APIRouter(prefix="/flocks", tags=["flocks"])


async def _owned_flock_or_404(db: AsyncSession, flock_id: int, user: User) -> Flock:
    flock = await db.get(Flock, flock_id)
    if flock is None or flock.user_id != user.user_id:
        raise HTTPException(status_code=404, detail="Flock not found.")
    return flock


@router.get("", response_model=list[FlockRead])
async def list_flocks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Flock]:
    stmt = select(Flock).where(Flock.user_id == current_user.user_id)
    return list(await db.scalars(stmt.order_by(Flock.flock_id)))


@router.post("", response_model=FlockRead, status_code=status.HTTP_201_CREATED)
async def create_flock(
    payload: FlockCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Flock:
    flock = Flock(
        user_id=current_user.user_id,
        name=payload.name,
        type=payload.type.value,
        current_age_weeks=payload.current_age_weeks,
        flock_size=payload.flock_size,
    )
    db.add(flock)
    await db.flush()
    await db.refresh(flock)
    return flock


@router.get("/{flock_id}", response_model=FlockRead)
async def get_flock(
    flock_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Flock:
    return await _owned_flock_or_404(db, flock_id, current_user)


@router.patch("/{flock_id}", response_model=FlockRead)
async def update_flock(
    flock_id: int,
    payload: FlockUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Flock:
    flock = await _owned_flock_or_404(db, flock_id, current_user)
    data = payload.model_dump(exclude_unset=True)
    if "type" in data and data["type"] is not None:
        data["type"] = data["type"].value
    for field, value in data.items():
        setattr(flock, field, value)
    await db.flush()
    return flock


@router.delete("/{flock_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flock(
    flock_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    flock = await _owned_flock_or_404(db, flock_id, current_user)
    await db.delete(flock)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
