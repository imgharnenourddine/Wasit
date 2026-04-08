from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
