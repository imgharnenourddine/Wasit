import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.institution import Class
from app.models.user import User
from app.schemas.delegate import (
    AIDelegateResponse,
    AIDelegateUpsert,
    ExamEventIn,
    ExamEventResponse,
    FiliereAISettingsPatch,
    TimetableSlotIn,
)
from app.schemas.institution import AssignDelegateRequest, ClassCreate, ClassResponse, FiliereResponse
from app.services.delegate_service import (
    add_exam_events,
    assert_can_manage_class,
    create_class_as_chef,
    patch_filiere_ai_settings,
    replace_timetable,
    upsert_ai_delegate,
)
from app.services.institutional_service import assign_delegate

router = APIRouter(tags=["ai-delegate"])


@router.patch("/filieres/{filiere_id}/classes/{class_id}/delegate", response_model=ClassResponse)
async def chef_assign_delegate(
    filiere_id: uuid.UUID,
    class_id: uuid.UUID,
    payload: AssignDelegateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ClassResponse:
    c = await db.get(Class, class_id)
    if not c or c.filiere_id != filiere_id:
        raise HTTPException(status_code=404, detail="Class not found in this filière")
    await assert_can_manage_class(db, current_user, class_id)
    updated = await assign_delegate(db, class_id, payload.user_id)
    return ClassResponse.model_validate(updated)


@router.post("/filieres/{filiere_id}/classes", response_model=ClassResponse)
async def chef_create_class(
    filiere_id: uuid.UUID,
    payload: ClassCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ClassResponse:
    c = await create_class_as_chef(db, current_user, filiere_id, payload)
    return ClassResponse.model_validate(c)


@router.patch("/filieres/{filiere_id}/ai-settings", response_model=FiliereResponse)
async def patch_filiere_poll_settings(
    filiere_id: uuid.UUID,
    payload: FiliereAISettingsPatch,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FiliereResponse:
    f = await patch_filiere_ai_settings(db, current_user, filiere_id, payload.aggregation_poll_threshold)
    return FiliereResponse.model_validate(f)


@router.put("/classes/{class_id}/ai-delegate", response_model=AIDelegateResponse)
async def put_ai_delegate_config(
    class_id: uuid.UUID,
    payload: AIDelegateUpsert,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AIDelegateResponse:
    row = await upsert_ai_delegate(db, current_user, class_id, payload)
    return AIDelegateResponse.model_validate(row)


@router.put("/classes/{class_id}/timetable")
async def put_class_timetable(
    class_id: uuid.UUID,
    slots: list[TimetableSlotIn],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, int | str]:
    n = await replace_timetable(db, current_user, class_id, slots)
    return {"class_id": str(class_id), "slots_saved": n}


@router.post("/classes/{class_id}/exams", response_model=list[ExamEventResponse])
async def post_class_exams(
    class_id: uuid.UUID,
    events: list[ExamEventIn],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ExamEventResponse]:
    rows = await add_exam_events(db, current_user, class_id, events)
    return [ExamEventResponse.model_validate(r) for r in rows]
