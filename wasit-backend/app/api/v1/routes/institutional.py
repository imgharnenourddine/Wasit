import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.auth import User
from app.schemas.institution import (
    AssignDelegateRequest,
    ClassCreate,
    ClassResponse,
    FiliereCreate,
    FiliereResponse,
    SchoolCreate,
    SchoolResponse,
)
from app.services.institutional_service import (
    assign_delegate,
    create_class,
    create_filiere,
    create_school,
    get_class_with_details,
    get_schools,
)

router = APIRouter(tags=["institutional"])


@router.post("/schools", response_model=SchoolResponse)
async def create_school_route(
    payload: SchoolCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_role("admin"))],
) -> SchoolResponse:
    school = await create_school(db, payload)
    return SchoolResponse.model_validate(school)


@router.get("/schools", response_model=list[SchoolResponse])
async def get_schools_route(db: Annotated[AsyncSession, Depends(get_db)]) -> list[SchoolResponse]:
    schools = await get_schools(db)
    return [SchoolResponse.model_validate(item) for item in schools]


@router.post("/filieres", response_model=FiliereResponse)
async def create_filiere_route(
    payload: FiliereCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_role("admin"))],
) -> FiliereResponse:
    filiere = await create_filiere(db, payload)
    return FiliereResponse.model_validate(filiere)


@router.post("/classes", response_model=ClassResponse)
async def create_class_route(
    payload: ClassCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_role("admin"))],
) -> ClassResponse:
    class_room = await create_class(db, payload)
    return ClassResponse.model_validate(class_room)


@router.patch("/classes/{class_id}/delegate", response_model=ClassResponse)
async def assign_delegate_route(
    class_id: uuid.UUID,
    payload: AssignDelegateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_role("admin"))],
) -> ClassResponse:
    class_room = await assign_delegate(db, class_id, payload.user_id)
    return ClassResponse.model_validate(class_room)


@router.get("/classes/{class_id}")
async def get_class_details_route(
    class_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> dict:
    return await get_class_with_details(db, class_id)
