"""API routes for file uploads and retrieval."""

from fastapi import APIRouter

router = APIRouter(prefix="/files", tags=["files"])
