"""API routes for the agent pipeline (classifier, aggregator, etc.)."""

from fastapi import APIRouter

router = APIRouter(prefix="/agents", tags=["agents"])
