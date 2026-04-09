import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.institution import Class
from app.models.user import User
from app.schemas.delegate import (
    AIDelegateResponse,
    AIDelegateUpsert,
    FiliereAISettingsPatch,
    FilierePDFDocumentResponse,
)
from app.schemas.institution import AssignDelegateRequest, ClassCreate, ClassResponse, FiliereResponse
from app.services.delegate_service import (
    assert_can_manage_class,
    create_class_as_chef,
    patch_filiere_ai_settings,
    upload_filiere_pdf,
    upsert_ai_delegate,
)
from app.services.institutional_service import assign_delegate
from app.services.pdf_service import get_filiere_document

router = APIRouter(tags=["ai-delegate"])

DocType = Literal["timetable", "exam_schedule"]


# ---------------------------------------------------------------------------
# Filière-level: PDF document upload & retrieval
# ---------------------------------------------------------------------------

@router.post(
    "/filieres/{filiere_id}/documents/{doc_type}",
    response_model=FilierePDFDocumentResponse,
    summary="Upload a timetable or exam-schedule PDF for a filière",
)
async def upload_filiere_document(
    filiere_id: uuid.UUID,
    doc_type: DocType,
    file: Annotated[UploadFile, File(description="PDF file from the external scheduling system")],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FilierePDFDocumentResponse:
    """Chef de filière or admin uploads a PDF.

    - Validates it is a PDF.
    - Extracts full text with PyMuPDF.
    - Stores extracted text in the DB (replaces any previous doc of the same type).
    - Saves the original file to Cloudinary.
    """
    row = await upload_filiere_pdf(db, current_user, filiere_id, doc_type, file)
    return FilierePDFDocumentResponse.model_validate(row)


@router.get(
    "/filieres/{filiere_id}/documents/{doc_type}",
    response_model=FilierePDFDocumentResponse,
    summary="Get the current PDF document metadata for a filière",
)
async def get_filiere_document_endpoint(
    filiere_id: uuid.UUID,
    doc_type: DocType,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> FilierePDFDocumentResponse:
    doc = await get_filiere_document(db, filiere_id, doc_type)
    if doc is None:
        raise HTTPException(
            status_code=404,
            detail=f"No {doc_type} document uploaded for this filière yet.",
        )
    return FilierePDFDocumentResponse.model_validate(doc)


# ---------------------------------------------------------------------------
# Filière-level: class management & AI settings
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Class-level: AI delegate config
# ---------------------------------------------------------------------------

@router.put("/classes/{class_id}/ai-delegate", response_model=AIDelegateResponse)
async def put_ai_delegate_config(
    class_id: uuid.UUID,
    payload: AIDelegateUpsert,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AIDelegateResponse:
    row = await upsert_ai_delegate(db, current_user, class_id, payload)
    return AIDelegateResponse.model_validate(row)
