import uuid

from pydantic import BaseModel, Field


class AgentDryRunRequest(BaseModel):
    """Admin dry-run: no ticket creation, no DB aggregation (classifier → router → summary only)."""

    raw_text: str = Field(min_length=5, max_length=4000)
    class_id: uuid.UUID
    student_id: uuid.UUID
