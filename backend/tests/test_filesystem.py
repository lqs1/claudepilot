"""Tests for filesystem API."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest


@pytest.mark.asyncio
async def test_get_home(client: Any) -> None:
    """The home endpoint returns the user's home directory."""
    response = await client.get("/api/fs/home")
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == str(Path.home().resolve())


@pytest.mark.asyncio
async def test_browse_absolute(client: Any) -> None:
    """Browsing an absolute path returns directory entries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        Path(tmpdir, "README.md").write_text("hello")
        Path(tmpdir, "src").mkdir()

        response = await client.get("/api/fs/browse-absolute", params={"path": tmpdir})
        assert response.status_code == 200
        data = response.json()
        assert data["current_path"] == str(Path(tmpdir).resolve())
        names = {entry["name"] for entry in data["entries"]}
        assert "README.md" in names
        assert "src" in names


@pytest.mark.asyncio
async def test_browse_absolute_default_to_home(client: Any) -> None:
    """Browsing without a path defaults to the home directory."""
    response = await client.get("/api/fs/browse-absolute")
    assert response.status_code == 200
    data = response.json()
    assert data["current_path"] == str(Path.home().resolve())


@pytest.mark.asyncio
async def test_read_file(client: Any) -> None:
    """Reading a file returns its contents."""
    with tempfile.TemporaryDirectory() as tmpdir:
        Path(tmpdir, "note.txt").write_text("line one\nline two", encoding="utf-8")

        response = await client.post(
            "/api/projects", json={"name": "FsRead", "path": tmpdir}
        )
        assert response.status_code == 200
        project_id = response.json()["project"]["id"]

        response = await client.get(
            "/api/fs/read",
            params={"project_id": project_id, "path": "note.txt"},
        )
        assert response.status_code == 200
        assert response.json()["content"] == "line one\nline two"


@pytest.mark.asyncio
async def test_write_file(client: Any) -> None:
    """Writing a file updates its contents."""
    with tempfile.TemporaryDirectory() as tmpdir:
        response = await client.post(
            "/api/projects", json={"name": "FsWrite", "path": tmpdir}
        )
        assert response.status_code == 200
        project_id = response.json()["project"]["id"]

        response = await client.put(
            "/api/fs/write",
            json={"project_id": project_id, "path": "new.txt", "content": "updated"},
        )
        assert response.status_code == 200

        assert Path(tmpdir, "new.txt").read_text(encoding="utf-8") == "updated"


@pytest.mark.asyncio
async def test_path_escape_returns_403(client: Any) -> None:
    """Accessing paths outside the project root is forbidden."""
    with tempfile.TemporaryDirectory() as tmpdir:
        response = await client.post(
            "/api/projects", json={"name": "FsEscape", "path": tmpdir}
        )
        assert response.status_code == 200
        project_id = response.json()["project"]["id"]

        response = await client.get(
            "/api/fs/read",
            params={"project_id": project_id, "path": "../etc/passwd"},
        )
        assert response.status_code == 403
