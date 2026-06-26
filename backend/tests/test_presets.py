"""Tests for the presets API."""

from __future__ import annotations

from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

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
async def test_list_empty(client: AsyncClient) -> None:
    response = await client.get("/api/presets")
    assert response.status_code == 200
    assert response.json() == {"presets": []}


@pytest.mark.asyncio
async def test_create_and_list(client: AsyncClient) -> None:
    response = await client.post(
        "/api/presets",
        json={"name": "快速", "settings": {"model": "opus", "effort": "high"}},
    )
    assert response.status_code == 200
    preset = response.json()["preset"]
    assert preset["name"] == "快速"
    # Created settings are kept, only allowed keys.
    assert preset["settings"]["model"] == "opus"
    assert preset["settings"]["effort"] == "high"

    response = await client.get("/api/presets")
    assert len(response.json()["presets"]) == 1


@pytest.mark.asyncio
async def test_create_requires_name(client: AsyncClient) -> None:
    response = await client.post("/api/presets", json={"name": "", "settings": {}})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_duplicate_name_conflict(client: AsyncClient) -> None:
    await client.post("/api/presets", json={"name": "dup", "settings": {}})
    response = await client.post("/api/presets", json={"name": "dup", "settings": {}})
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_unknown_keys_dropped(client: AsyncClient) -> None:
    """Preset storage drops anything outside the allowed key set."""
    response = await client.post(
        "/api/presets",
        json={
            "name": "p",
            "settings": {"model": "haiku", "evil": "delete-all", "mcp_servers": ["x"]},
        },
    )
    assert response.status_code == 200
    settings: dict[str, Any] = response.json()["preset"]["settings"]
    assert "evil" not in settings
    assert "mcp_servers" not in settings
    assert settings["model"] == "haiku"


@pytest.mark.asyncio
async def test_update_and_delete(client: AsyncClient) -> None:
    created = await client.post(
        "/api/presets", json={"name": "orig", "settings": {"effort": "low"}}
    )
    preset_id = created.json()["preset"]["id"]

    updated = await client.put(
        f"/api/presets/{preset_id}",
        json={"name": "renamed", "settings": {"effort": "max"}},
    )
    assert updated.status_code == 200
    assert updated.json()["preset"]["name"] == "renamed"
    assert updated.json()["preset"]["settings"]["effort"] == "max"

    deleted = await client.delete(f"/api/presets/{preset_id}")
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": True}

    # Gone afterwards.
    response = await client.get("/api/presets")
    assert response.json() == {"presets": []}


@pytest.mark.asyncio
async def test_delete_unknown_returns_404(client: AsyncClient) -> None:
    response = await client.delete("/api/presets/does-not-exist")
    assert response.status_code == 404
