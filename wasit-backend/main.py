from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.api.v1.routes.agents import router as agents_router
from app.api.v1.routes.analytics import router as analytics_router
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.files import router as files_router
from app.api.v1.routes.institutional import router as institutional_router
from app.api.v1.routes.notifications import router as notifications_router
from app.api.v1.routes.students import router as students_router
from app.api.v1.routes.telegram import router as telegram_router
from app.api.v1.routes.tickets import router as tickets_router
from app.core.config import settings
from app.core.database import SessionLocal, init_db
from app.services.tickets import auto_escalate_overdue_tickets

app = FastAPI(title=settings.app_name, version="1.0.0")


@app.middleware("http")
async def unhandled_error_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except HTTPException:
        raise
    except Exception as exc:
        return JSONResponse(status_code=500, content={"detail": str(exc)})


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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


API_PREFIX = settings.api_prefix
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(institutional_router, prefix=API_PREFIX)
app.include_router(students_router, prefix=API_PREFIX)
app.include_router(tickets_router, prefix=API_PREFIX)
app.include_router(files_router, prefix=API_PREFIX)
app.include_router(notifications_router, prefix=API_PREFIX)
app.include_router(telegram_router, prefix=API_PREFIX)
app.include_router(agents_router, prefix=API_PREFIX)
app.include_router(analytics_router, prefix=API_PREFIX)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "version": "1.0.0"}
