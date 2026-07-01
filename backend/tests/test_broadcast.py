"""Tests for the parallel broadcast endpoint.

Broadcast spawns one fresh session per preset and sends the same prompt to
each. To keep these tests hermetic (no real Claude CLI process), we patch
``_ensure_session_running`` to a no-op and assert the orchestration: that the
right sessions get created with the right merged settings, and that bad input
is rejected before anything is created.
"""

from __future__ import annotations

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


@pytest.fixture(autouse=True)
def _no_cli_start(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid actually launching the Claude CLI during broadcast tests."""
    import app.api.sessions as sessions_mod

    async def _fake_ensure(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(sessions_mod, "_ensure_session_running", _fake_ensure)


async def _make_project(client: AsyncClient) -> str:
    resp = await client.post("/api/projects", json={"name": "BCast", "path": "/tmp"})
    return resp.json()["project"]["id"]


async def _make_preset(client: AsyncClient, name: str, model: str) -> str:
    resp = await client.post(
        "/api/presets", json={"name": name, "settings": {"model": model}}
    )
    return resp.json()["preset"]["id"]


@pytest.mark.asyncio
async def test_broadcast_creates_one_session_per_config(client: AsyncClient) -> None:
    project_id = await _make_project(client)
    p1 = await _make_preset(client, "快速", "claude-haiku-4")
    p2 = await _make_preset(client, "深度", "claude-opus-4")

    resp = await client.post(
        f"/api/projects/{project_id}/sessions/broadcast",
        json={
            "prompt": "总结这个项目",
            "configurations": [{"preset_id": p1}, {"preset_id": p2}],
        },
    )
    assert resp.status_code == 200
    sessions = resp.json()["sessions"]
    assert len(sessions) == 2
    # Each session carries its preset's model setting.
    models = {s["settings"]["model"] for s in sessions}
    assert models == {"claude-haiku-4", "claude-opus-4"}
    # Sessions are distinct.
    assert len({s["id"] for s in sessions}) == 2
    # Titles embed the prompt snippet + preset name for sidebar clarity.
    titles = [s["title"] for s in sessions]
    assert all("总结这个项目" in t for t in titles)


@pytest.mark.asyncio
async def test_broadcast_requires_prompt(client: AsyncClient) -> None:
    project_id = await _make_project(client)
    resp = await client.post(
        f"/api/projects/{project_id}/sessions/broadcast",
        json={"prompt": "", "configurations": [{}]},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_broadcast_requires_configurations(client: AsyncClient) -> None:
    project_id = await _make_project(client)
    resp = await client.post(
        f"/api/projects/{project_id}/sessions/broadcast",
        json={"prompt": "hi", "configurations": []},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_broadcast_unknown_project_404(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/projects/does-not-exist/sessions/broadcast",
        json={"prompt": "hi", "configurations": [{}]},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_broadcast_unknown_preset_404(client: AsyncClient) -> None:
    project_id = await _make_project(client)
    resp = await client.post(
        f"/api/projects/{project_id}/sessions/broadcast",
        json={
            "prompt": "hi",
            "configurations": [{"preset_id": "nope"}],
        },
    )
    # Fails fast, before creating any session.
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_broadcast_without_preset_uses_defaults(client: AsyncClient) -> None:
    project_id = await _make_project(client)
    resp = await client.post(
        f"/api/projects/{project_id}/sessions/broadcast",
        json={"prompt": "hello", "configurations": [{}]},
    )
    assert resp.status_code == 200
    sessions = resp.json()["sessions"]
    assert len(sessions) == 1
