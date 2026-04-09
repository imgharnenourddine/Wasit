"""AI Delegate intent labels (FEATURE_AI_DELEGATE §8 Phase 3)."""

from __future__ import annotations

from typing import Literal

DelegateIntent = Literal["autonomous_answer", "aggregate_request", "poll_needed", "unknown"]


def infer_delegate_intent(text: str, similar_count: int = 0, poll_threshold: int = 3) -> DelegateIntent:
    """Rule-based intent; LLM refinement can wrap this later."""
    t = text.lower().strip()
    if not t:
        return "unknown"

    poll_markers = ("poll", "sondage", "vote", "voter", "survey")
    if any(m in t for m in poll_markers):
        return "poll_needed"

    data_markers = (
        "emploi",
        "timetable",
        "schedule",
        "cours",
        "exam",
        "examen",
        "trombi",
        "étudiant",
        "student",
        "combien",
        "effectif",
    )
    if any(m in t for m in data_markers):
        return "autonomous_answer"

    if similar_count >= poll_threshold:
        return "poll_needed"

    if len(t) > 12 or "?" in t:
        return "aggregate_request"

    return "unknown"
