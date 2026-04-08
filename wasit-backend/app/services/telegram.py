from typing import Any


async def send_to_group(class_id: str, message: str) -> dict[str, Any]:
    # Temporary stub for Dev 2 phase-1 integration.
    return {
        "class_id": class_id,
        "message_preview": message[:120],
        "sent": True,
    }
