"""Tests for WebSocket streaming."""

from __future__ import annotations


import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """Provide an HTTP client with an isolated database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.skip(reason="Requires live Claude CLI; run manually")
def test_websocket_placeholder() -> None:
    """Placeholder for WebSocket integration tests."""


def _setup_project_and_session(client: TestClient) -> tuple[str, str]:
    """Create a project and session via HTTP for WebSocket tests."""
    response = client.post(
        "/api/projects", json={"name": "WS Test", "path": "/tmp/ws-test"}
    )
    assert response.status_code == 200
    project_id = response.json()["project_id"]

    response = client.post(
        f"/api/projects/{project_id}/sessions", json={"title": "WS Session"}
    )
    assert response.status_code == 200
    session_id = response.json()["session_id"]
    return project_id, session_id
