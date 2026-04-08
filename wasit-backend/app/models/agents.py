"""Compatibility re-exports for agent code; canonical models live in app.models.problem."""

from app.models.problem import AggregationGroup, Problem

__all__ = ["AggregationGroup", "Problem"]
