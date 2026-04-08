import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class StudentUserInfo(BaseModel):
    id: uuid.UUID
    email: EmailStr
    first_name: str
    last_name: str
    phone: str | None


class StudentResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    class_id: uuid.UUID
    student_number: str | None
    photo_url: str | None
    is_active: bool
    user: StudentUserInfo


class ProjectGroupsCreateRequest(BaseModel):
    group_size: int


class ProjectGroupMemberResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID


class ProjectGroupResponse(BaseModel):
    id: uuid.UUID
    class_id: uuid.UUID
    name: str
    created_at: datetime
    members: list[ProjectGroupMemberResponse] = []
