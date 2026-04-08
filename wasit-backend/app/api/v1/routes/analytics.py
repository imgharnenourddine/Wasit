import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.institution import Class, Filiere
from app.models.user import Role, User
from app.services.analytics_service import (
    get_class_patterns,
    get_filiere_stats,
    get_school_overview,
    get_ticket_trends,
    get_top_issues,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


async def _ensure_filiere_access(
    user: User,
    filiere_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    filiere = await db.get(Filiere, filiere_id)
    if not filiere:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filiere not found")
    if user.role == Role.admin:
        return
    if filiere.responsible_id == user.id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


async def _ensure_class_access(
    user: User,
    class_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    cls = await db.get(Class, class_id)
    if not cls:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")
    if user.role == Role.admin:
        return
    if user.role == Role.delegate and cls.delegate_id == user.id:
        return
    if user.role == Role.teacher:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


@router.get("/school/{school_id}")
async def school_overview(
    school_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_role("admin"))],
) -> dict:
    return await get_school_overview(db, school_id)


@router.get("/filiere/{filiere_id}")
async def filiere_stats(
    filiere_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    if current_user.role != Role.admin:
        await _ensure_filiere_access(current_user, filiere_id, db)
    return await get_filiere_stats(db, filiere_id)


@router.get("/class/{class_id}")
async def class_patterns(
    class_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    if current_user.role.value not in ("admin", "delegate", "teacher"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    await _ensure_class_access(current_user, class_id, db)
    return await get_class_patterns(db, class_id)


@router.get("/school/{school_id}/trends")
async def school_trends(
    school_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_role("admin"))],
    days: int = Query(default=30, ge=1, le=365),
) -> list[dict]:
    return await get_ticket_trends(db, school_id, days)


@router.get("/school/{school_id}/top-issues")
async def school_top_issues(
    school_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_role("admin"))],
    limit: int = Query(default=10, ge=1, le=100),
) -> list[dict]:
    return await get_top_issues(db, school_id, limit)
