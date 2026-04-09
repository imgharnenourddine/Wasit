import uuid
from datetime import datetime

from pydantic import BaseModel


class SchoolCreate(BaseModel):
    name: str
    domain: str


class SchoolResponse(BaseModel):
    id: uuid.UUID
    name: str
    domain: str
    created_at: datetime

    model_config = {"from_attributes": True}


class FiliereCreate(BaseModel):
    name: str
    school_id: uuid.UUID
    responsible_id: uuid.UUID | None = None


class FiliereResponse(BaseModel):
    id: uuid.UUID
    school_id: uuid.UUID
    name: str
    responsible_id: uuid.UUID | None
    aggregation_poll_threshold: int = 3
    created_at: datetime

    model_config = {"from_attributes": True}


class DelegateInfo(BaseModel):
    id: uuid.UUID
    email: str
    first_name: str
    last_name: str


class ClassCreate(BaseModel):
    name: str
    filiere_id: uuid.UUID
    academic_year: str


class ClassResponse(BaseModel):
    id: uuid.UUID
    filiere_id: uuid.UUID
    name: str
    academic_year: str
    delegate_id: uuid.UUID | None
    created_at: datetime
    delegate: DelegateInfo | None = None

    model_config = {"from_attributes": True}


class AssignDelegateRequest(BaseModel):
    user_id: uuid.UUID
