from typing import Any


async def notify_destination(destination: str, summary: str, ticket_id: str) -> dict[str, Any]:
    # Temporary stub for Dev 2 phase-1 integration.
    return {
        "destination": destination,
        "ticket_id": ticket_id,
        "summary_preview": summary[:120],
        "sent": True,
        "channel": "stub",
    }
