import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User
from app.schemas.students import ProjectGroupsCreateRequest, ProjectGroupResponse, StudentResponse
from app.services.file_service import parse_trombinoscope_csv, save_upload
from app.services.student_service import (
    bulk_create_students,
    generate_project_groups,
    get_class_project_groups,
    get_class_students,
)

router = APIRouter(tags=["students"])


@router.post("/classes/{class_id}/upload-trombinoscope")
async def upload_trombinoscope(
    class_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_role("admin", "delegate"))],
    file: UploadFile = File(...),
) -> dict:
    rows = await parse_trombinoscope_csv(file)
    await save_upload(file, os.path.join("uploads", "trombinoscopes", str(class_id)))
    return await bulk_create_students(db, class_id, rows)


@router.get("/classes/{class_id}/students", response_model=list[StudentResponse])
async def get_students_route(
    class_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[StudentResponse]:
    students = await get_class_students(db, class_id)
    response: list[StudentResponse] = []
    for student in students:
        response.append(
            StudentResponse(
                id=student.id,
                user_id=student.user_id,
                class_id=student.class_id,
                student_number=student.student_number,
                photo_url=student.photo_url,
                is_active=student.is_active,
                user={
                    "id": student.user.id,
                    "email": student.user.email,
                    "first_name": student.user.first_name,
                    "last_name": student.user.last_name,
                    "phone": student.user.phone,
                },
            )
        )
    return response


@router.post("/classes/{class_id}/project-groups", response_model=list[ProjectGroupResponse])
async def generate_project_groups_route(
    class_id: uuid.UUID,
    payload: ProjectGroupsCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_role("admin", "delegate"))],
) -> list[ProjectGroupResponse]:
    await generate_project_groups(db, class_id, payload.group_size)
    full_groups = await get_class_project_groups(db, class_id)
    return [
        ProjectGroupResponse(
            id=group.id,
            class_id=group.class_id,
            name=group.name,
            created_at=group.created_at,
            members=[{"id": member.id, "student_id": member.student_id} for member in group.members],
        )
        for group in full_groups
    ]


@router.get("/classes/{class_id}/project-groups", response_model=list[ProjectGroupResponse])
async def get_project_groups_route(
    class_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> list[ProjectGroupResponse]:
    groups = await get_class_project_groups(db, class_id)
    return [
        ProjectGroupResponse(
            id=group.id,
            class_id=group.class_id,
            name=group.name,
            created_at=group.created_at,
            members=[{"id": member.id, "student_id": member.student_id} for member in group.members],
        )
        for group in groups
    ]
