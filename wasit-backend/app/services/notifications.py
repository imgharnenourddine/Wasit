from collections import defaultdict
from uuid import UUID

from fastapi import WebSocket
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.user import Role, User


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        await websocket.accept()
        self._connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        if user_id in self._connections and websocket in self._connections[user_id]:
            self._connections[user_id].remove(websocket)
            if not self._connections[user_id]:
                del self._connections[user_id]

    async def send_to_user(self, user_id: str, message: dict) -> None:
        for ws in self._connections.get(user_id, []):
            await ws.send_json(message)


manager = ConnectionManager()

DESTINATION_ROLE_MAP: dict[str, Role] = {
    "teacher": Role.teacher,
    "admin": Role.admin,
    "listening": Role.listening,
    "delegate": Role.delegate,
    "emergency": Role.admin,
}


async def notify_destination(
    destination: str, summary: str, ticket_id: str, db: AsyncSession | None = None
) -> dict[str, str | int]:
    if db is None:
        return {"destination": destination, "ticket_id": ticket_id, "sent": 0}

    role = DESTINATION_ROLE_MAP.get(destination, Role.admin)
    users_result = await db.execute(select(User).where(User.role == role, User.is_active.is_(True)))
    users = list(users_result.scalars().all())

    for user in users:
        notification = Notification(
            user_id=user.id,
            title=f"New ticket routed to {destination}",
            body=summary,
            type="ticket",
        )
        db.add(notification)
        await manager.send_to_user(
            str(user.id),
            {"type": "ticket", "ticket_id": ticket_id, "destination": destination, "summary": summary},
        )
    await db.commit()
    return {"destination": destination, "ticket_id": ticket_id, "sent": len(users)}


async def get_user_notifications(db: AsyncSession, user_id: UUID, unread_only: bool = False) -> list[Notification]:
    stmt = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    stmt = stmt.order_by(Notification.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def mark_notification_read(db: AsyncSession, notification_id: UUID, user_id: UUID) -> Notification:
    notification = await db.get(Notification, notification_id)
    if not notification or notification.user_id != user_id:
        raise ValueError("Notification not found")
    notification.is_read = True
    await db.commit()
    await db.refresh(notification)
    return notification
