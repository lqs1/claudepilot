"""Tests for settings API."""

from __future__ import annotations

from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.services.setting_service import _DEFAULT_SETTINGS
from app.database import Base, engine
from app.main import app


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """Provide an HTTP client with an isolated database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_default_settings(client: AsyncClient) -> None:
    """Default settings are returned."""
    response = await client.get("/api/settings")
    assert response.status_code == 200
    data: dict[str, Any] = response.json()
    assert "settings" in data
    assert data["settings"]["model"] == _DEFAULT_SETTINGS["model"]
    assert data["settings"]["permission_mode"] == _DEFAULT_SETTINGS["permission_mode"]


@pytest.mark.asyncio
async def test_update_global_settings(client: AsyncClient) -> None:
    """Global settings can be updated."""
    response = await client.put(
        "/api/settings", json={"model": "claude-opus-4", "permission_mode": "acceptAll"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["settings"]["model"] == "claude-opus-4"
    assert data["settings"]["permission_mode"] == "acceptAll"

    # Reset
    await client.put(
        "/api/settings",
        json={
            "model": _DEFAULT_SETTINGS["model"],
            "permission_mode": _DEFAULT_SETTINGS["permission_mode"],
        },
    )


@pytest.mark.asyncio
async def test_update_settings_rejects_unknown_key(client: AsyncClient) -> None:
    """Unknown setting keys are rejected."""
    response = await client.put("/api/settings", json={"unknown_key": "value"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_session_settings_merge(client: AsyncClient) -> None:
    """Session settings merge with global defaults."""
    # Create project and session
    response = await client.post(
        "/api/projects", json={"name": "Settings Test", "path": "/tmp/settings-test"}
    )
    assert response.status_code == 200
    project_id = response.json()["project"]["id"]

    response = await client.post(
        f"/api/projects/{project_id}/sessions",
        json={
            "title": "Test",
            "language": "zh",
            "settings": {"model": "claude-opus-4"},
        },
    )
    assert response.status_code == 200
    session_id = response.json()["session"]["id"]
    assert response.json()["session"]["settings"]["model"] == "claude-opus-4"

    # Get merged settings
    response = await client.get(f"/api/settings/session/{session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["settings"]["model"] == "claude-opus-4"
    assert data["settings"]["permission_mode"] == _DEFAULT_SETTINGS["permission_mode"]


@pytest.mark.asyncio
async def test_update_session_settings(client: AsyncClient) -> None:
    """Session-specific settings can be updated."""
    response = await client.post(
        "/api/projects",
        json={"name": "Settings Test 2", "path": "/tmp/settings-test-2"},
    )
    assert response.status_code == 200
    project_id = response.json()["project"]["id"]

    response = await client.post(
        f"/api/projects/{project_id}/sessions", json={"title": "Test", "language": "zh"}
    )
    assert response.status_code == 200
    session_id = response.json()["session"]["id"]

    response = await client.put(
        f"/api/settings/session/{session_id}", json={"permission_mode": "acceptAll"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["settings"]["permission_mode"] == "acceptAll"
    assert data["settings"]["model"] == _DEFAULT_SETTINGS["model"]


@pytest.mark.asyncio
async def test_session_settings_not_found(client: AsyncClient) -> None:
    """404 for non-existent session."""
    response = await client.get("/api/settings/session/non-existent-id")
    assert response.status_code == 404, f"Got {response.status_code}: {response.text}"

    response = await client.put(
        "/api/settings/session/non-existent-id", json={"model": "x"}
    )
    assert response.status_code == 404, f"Got {response.status_code}: {response.text}"
