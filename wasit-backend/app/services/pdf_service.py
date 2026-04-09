"""PDF upload and text-extraction service for the AI delegate bot.

Flow (per upload):
  1. Validate file is a PDF.
  2. Upload original file to Cloudinary (resource_type=raw).
  3. Extract full text from the PDF using PyMuPDF (fitz).
  4. Upsert a FilierePDFDocument row (one per filière × doc_type).
"""

from __future__ import annotations

from asyncio import to_thread
from uuid import UUID

import fitz  # PyMuPDF
import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.delegate_data import FilierePDFDocument

# reuse the same Cloudinary config as file_service.py
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)

_VALID_DOC_TYPES = {"timetable", "exam_schedule"}


def _extract_text_sync(pdf_bytes: bytes) -> str:
    """Extract all text from a PDF byte buffer (runs synchronously, offloaded to thread)."""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        pages = [page.get_text() for page in doc]
    return "\n".join(pages).strip()


async def extract_text_from_pdf(file: UploadFile) -> str:
    """Read the UploadFile, validate it's a PDF, and return extracted plain text."""
    if not _is_pdf(file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted.",
        )
    pdf_bytes = await file.read()
    await file.seek(0)
    return await to_thread(_extract_text_sync, pdf_bytes)


def _is_pdf(file: UploadFile) -> bool:
    name: str = (file.filename or "").lower()
    ctype: str = (file.content_type or "").lower()
    return name.endswith(".pdf") or "pdf" in ctype


async def save_filiere_pdf(
    db: AsyncSession,
    filiere_id: UUID,
    doc_type: str,
    upload: UploadFile,
) -> FilierePDFDocument:
    """Upload a PDF for a filière, extract its text, and upsert the DB row.

    Args:
        db: Async SQLAlchemy session.
        filiere_id: UUID of the target Filiere.
        doc_type: ``"timetable"`` or ``"exam_schedule"``.
        upload: The PDF file from the multipart request.

    Returns:
        The upserted FilierePDFDocument ORM instance (refreshed).
    """
    if doc_type not in _VALID_DOC_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"doc_type must be one of: {', '.join(sorted(_VALID_DOC_TYPES))}",
        )

    if not _is_pdf(upload):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted.",
        )

    pdf_bytes = await upload.read()
    await upload.seek(0)

    # 1. Upload to Cloudinary
    safe_name = (upload.filename or f"{doc_type}.pdf").rsplit(".", 1)[0]
    folder = f"wasit/filieres/{filiere_id}/{doc_type}"
    cloudinary_result = await to_thread(
        cloudinary.uploader.upload,
        pdf_bytes,
        resource_type="raw",
        folder=folder,
        public_id=safe_name,
        overwrite=True,
    )
    cloudinary_url: str = str(cloudinary_result["secure_url"])

    # 2. Extract text
    extracted_text = await to_thread(_extract_text_sync, pdf_bytes)
    if not extracted_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract any text from the PDF. Please check the file.",
        )

    # 3. Upsert (one doc per filière × doc_type)
    result = await db.execute(
        select(FilierePDFDocument).where(
            FilierePDFDocument.filiere_id == filiere_id,
            FilierePDFDocument.doc_type == doc_type,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.filename = upload.filename or f"{doc_type}.pdf"
        row.extracted_text = extracted_text
        row.cloudinary_url = cloudinary_url
    else:
        row = FilierePDFDocument(
            filiere_id=filiere_id,
            doc_type=doc_type,
            filename=upload.filename or f"{doc_type}.pdf",
            extracted_text=extracted_text,
            cloudinary_url=cloudinary_url,
        )
        db.add(row)

    await db.commit()
    await db.refresh(row)
    return row


async def get_filiere_document(
    db: AsyncSession,
    filiere_id: UUID,
    doc_type: str,
) -> FilierePDFDocument | None:
    """Return the current PDF document for a filière, or None if not uploaded yet."""
    result = await db.execute(
        select(FilierePDFDocument).where(
            FilierePDFDocument.filiere_id == filiere_id,
            FilierePDFDocument.doc_type == doc_type,
        )
    )
    return result.scalar_one_or_none()
