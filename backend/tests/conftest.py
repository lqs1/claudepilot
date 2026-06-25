"""Shared pytest fixtures for backend tests."""

from __future__ import annotations

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.database as database_module
from app.database import Base
from app.main import app


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """Provide an HTTP client with an isolated in-memory database."""
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    test_session_maker = async_sessionmaker(
        test_engine, class_=database_module.AsyncSession, expire_on_commit=False
    )

    original_engine = database_module.engine
    original_session_maker = database_module.async_session_maker

    database_module.engine = test_engine
    database_module.async_session_maker = test_session_maker

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()

    database_module.engine = original_engine
    database_module.async_session_maker = original_session_maker
