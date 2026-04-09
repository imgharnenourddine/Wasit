"""Debug-only route to test the AI delegate RAG pipeline via HTTP.

This endpoint lets you verify that autonomous_reply_from_tools correctly
answers questions using the uploaded PDF text (timetable / exam_schedule).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.user import User
from app.services.ai_delegate_tools import autonomous_reply_from_tools

router = APIRouter(prefix="/debug", tags=["debug"])


class AIQueryRequest(BaseModel):
    class_id: UUID
    question: str


@router.post("/ai-query")
async def debug_ai_query(
    payload: AIQueryRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_role("admin"))],
) -> dict:
    """Call autonomous_reply_from_tools directly (admin only, for testing)."""
    answer = await autonomous_reply_from_tools(db, payload.class_id, payload.question)
    return {
        "question": payload.question,
        "answer": answer,
        "answered": answer is not None,
    }
