"""Tests for project and session APIs."""

from __future__ import annotations

import tempfile
from pathlib import Path
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
async def test_create_and_list_project(client: AsyncClient) -> None:
    """A project can be created and then listed."""
    response = await client.post(
        "/api/projects", json={"name": "Test Project", "path": "/tmp/test-project"}
    )
    assert response.status_code == 200
    data: dict[str, Any] = response.json()
    assert data["project"]["name"] == "Test Project"

    response = await client.get("/api/projects")
    assert response.status_code == 200
    projects = response.json()["projects"]
    assert len(projects) == 1


@pytest.mark.asyncio
async def test_create_session(client: AsyncClient) -> None:
    """A session can be created under a project."""
    response = await client.post(
        "/api/projects",
        json={"name": "Test Project", "path": "/tmp/test-session-project"},
    )
    assert response.status_code == 200
    project_id = response.json()["project"]["id"]

    response = await client.post(
        f"/api/projects/{project_id}/sessions",
        json={"title": "Test Session", "language": "zh"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["session"]["title"] == "Test Session"
    assert data["session"]["language"] == "zh"
    assert data["session"]["project_id"] == project_id


@pytest.mark.asyncio
async def test_open_project_from_local_path(client: AsyncClient) -> None:
    """Opening a local directory creates a project using the directory name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        response = await client.post("/api/projects/open", json={"path": tmpdir})
        assert response.status_code == 200
        data = response.json()
        assert data["project"]["name"] == Path(tmpdir).name
        assert data["project"]["path"] == str(Path(tmpdir).resolve())


@pytest.mark.asyncio
async def test_open_project_invalid_path(client: AsyncClient) -> None:
    """Opening a non-existent path returns 400."""
    response = await client.post("/api/projects/open", json={"path": "/does/not/exist"})
    assert response.status_code == 400
