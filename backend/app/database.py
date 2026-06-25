"""Async database configuration."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import DATABASE_URL, DATA_DIR

DATA_DIR.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


async def init_db() -> None:
    """Create database tables if they do not already exist."""
    # Import models so that Base.metadata knows about all tables.
    from app import models  # noqa: F401

    async with engine.begin() as conn:

        def _create_tables(sync_conn: Any) -> None:
            from sqlalchemy import inspect

            inspector = inspect(sync_conn)
            existing = set(inspector.get_table_names())
            target = set(Base.metadata.tables.keys())
            if not target.issubset(existing):
                Base.metadata.create_all(sync_conn)

        await conn.run_sync(_create_tables)


async def close_db() -> None:
    """Dispose the database engine."""
    await engine.dispose()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for dependency injection."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
