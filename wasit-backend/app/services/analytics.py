"""
Analytics query implementations live in `analytics_service.py` (used by API routes).

This module is kept for a stable import path; use `analytics_service` for new code.
"""

from app.services import analytics_service

__all__ = ["analytics_service"]
