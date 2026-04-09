import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def _engine_connect_args() -> dict:
    # asyncpg: connection establishment timeout (seconds) so slow DB does not hang forever
    if settings.DATABASE_URL.startswith("postgresql"):
        return {"timeout": 15}
    return {}


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    connect_args=_engine_connect_args(),
)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    """Create tables from metadata (dev convenience; use Alembic in production)."""
    from app import models  # noqa: F401

    logger.info("init_db: connecting and creating tables if missing")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("init_db: finished")


async def init_db_background() -> None:
    """Run `init_db` with error logging (for asyncio.create_task from app startup)."""
    try:
        await init_db()
    except Exception:
        logger.exception("init_db_background: schema init failed")
