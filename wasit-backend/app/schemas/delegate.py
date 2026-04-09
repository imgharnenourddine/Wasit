import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AIDelegateUpsert(BaseModel):
    personality_prompt: str | None = None
    is_active: bool = True


class AIDelegateResponse(BaseModel):
    id: uuid.UUID
    class_id: uuid.UUID
    personality_prompt: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TimetableSlotIn(BaseModel):
    day_of_week: int = Field(ge=0, le=6, description="0=Monday … 6=Sunday")
    start_time: str = Field(examples=["09:00"])
    end_time: str
    subject: str
    room: str | None = None
    teacher_name: str | None = None


class ExamEventIn(BaseModel):
    title: str
    subject: str | None = None
    starts_at: datetime
    room: str | None = None


class ExamEventResponse(BaseModel):
    id: uuid.UUID
    class_id: uuid.UUID
    title: str
    subject: str | None
    starts_at: datetime
    room: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class FiliereAISettingsPatch(BaseModel):
    aggregation_poll_threshold: int = Field(ge=1, le=100)
