"""API routes for ticket lifecycle."""

from fastapi import APIRouter

router = APIRouter(prefix="/tickets", tags=["tickets"])
