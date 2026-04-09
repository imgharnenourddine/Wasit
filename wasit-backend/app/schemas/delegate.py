import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

DOC_TYPE = Literal["timetable", "exam_schedule"]


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


class FilierePDFDocumentResponse(BaseModel):
    id: uuid.UUID
    filiere_id: uuid.UUID
    doc_type: DOC_TYPE
    filename: str
    extracted_text: str
    cloudinary_url: str
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class FiliereAISettingsPatch(BaseModel):
    aggregation_poll_threshold: int = Field(ge=1, le=100)
