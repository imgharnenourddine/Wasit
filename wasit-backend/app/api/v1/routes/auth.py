"""API routes for authentication (login, refresh, register)."""

from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])
