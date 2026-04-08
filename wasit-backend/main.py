from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.notifications import router as notifications_router
from app.api.v1.routes.telegram import router as telegram_router
from app.api.v1.routes.tickets import router as tickets_router
from app.core.config import settings
from app.core.database import SessionLocal, init_db
from app.services.tickets import auto_escalate_overdue_tickets

app = FastAPI(title=settings.app_name)
app.include_router(tickets_router, prefix=settings.api_prefix)
app.include_router(telegram_router, prefix=settings.api_prefix)
app.include_router(notifications_router, prefix=settings.api_prefix)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    await init_db()
    scheduler = AsyncIOScheduler()

    async def _escalation_job() -> None:
        async with SessionLocal() as db:
            await auto_escalate_overdue_tickets(db)

    scheduler.add_job(_escalation_job, "interval", hours=1)
    scheduler.start()


app.include_router(auth_router, prefix="/api/v1")


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "version": "1.0.0"}
