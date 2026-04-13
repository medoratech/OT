from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,    # test connection before use — prevents "connection is closed"
    pool_recycle=300,      # recycle connections every 5 min (Neon closes idle after ~5 min)
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """Create all tables on startup."""
    async with engine.begin() as conn:
        from models import user, ot_note, patient  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
