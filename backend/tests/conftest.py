"""Shared pytest fixtures for backend tests.

CRITICAL: the env var set at the top MUST be configured before anything
imports app.database, so the suite always uses a throwaway DB file and can
NEVER drop the user's real ~/.claudepilot/claudepilot.db.

The recurring "no such table: projects" at runtime came from test fixtures
running ``drop_all`` on the real module-level engine (imported by name), then
init_db only runs at server startup — so.prod would start against an emptied
DB. Routing everything through one env-selected test file fixes this for good.
"""

import os
import tempfile
from pathlib import Path

_TEST_DB = Path(tempfile.gettempdir()) / "claudepilot_test.db"
if _TEST_DB.exists():
    _TEST_DB.unlink()
os.environ["CLAUDEPILOT_DB_URL"] = f"sqlite+aiosqlite:///{_TEST_DB}"

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

import app.database as database_module  # noqa: E402
from app.database import Base  # noqa: E402
from app.main import app  # noqa: E402


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """Provide an HTTP client with an isolated DB.

    Uses the app's own engine (already pointed at the throwaway test DB by
    the env var above). create_all/drop_all here therefore act on that test
    DB only — never the real one. Tables are recreated fresh per test.
    """
    async with database_module.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    async with database_module.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
