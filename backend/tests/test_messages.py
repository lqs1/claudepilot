"""Integration tests for message sending and Claude responses.

History lives in the CLI's jsonl (see HistoryService). These tests drive the
real CLI over HTTP and assert that the reply surfaces through the jsonl-based
``GET /messages`` endpoint.
"""

from __future__ import annotations

import asyncio
import uuid

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


@pytest.mark.asyncio
async def test_send_message_receives_assistant_reply(client: AsyncClient) -> None:
    """Sending a message starts Claude; the reply is readable via history."""
    # Use a unique path so this session's jsonl is isolated.
    response = await client.post(
        "/api/projects",
        json={"name": f"MsgTest-{uuid.uuid4().hex[:6]}", "path": "/tmp"},
    )
    assert response.status_code == 200
    project_id = response.json()["project"]["id"]

    response = await client.post(
        f"/api/projects/{project_id}/sessions",
        json={"title": "Test Session", "language": "en"},
    )
    assert response.status_code == 200
    session_id = response.json()["session"]["id"]

    # Send a message that Claude should answer deterministically.
    response = await client.post(
        f"/api/sessions/{session_id}/messages",
        json={"content": "Say exactly the word 'pong' and nothing else."},
        timeout=30,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "sent"

    # The reply surfaces in the jsonl-backed history (poll until it appears).
    assistant_text = ""
    for _ in range(50):
        resp = await client.get(f"/api/sessions/{session_id}/messages")
        messages = resp.json()["messages"]
        assistant_messages = [m for m in messages if m["role"] == "assistant"]
        if assistant_messages and assistant_messages[-1]["content"]:
            assistant_text = assistant_messages[-1]["content"]
            break
        await asyncio.sleep(0.5)

    assert assistant_text, "No assistant reply appeared in history"
    # Every history message carries the turn uuid used for deletion.
    assert all(m.get("uuid") for m in messages)


@pytest.mark.asyncio
async def test_resume_session(client: AsyncClient) -> None:
    """A stopped session can be resumed."""
    response = await client.post(
        "/api/projects",
        json={"name": f"ResumeTest-{uuid.uuid4().hex[:6]}", "path": "/tmp"},
    )
    assert response.status_code == 200
    project_id = response.json()["project"]["id"]

    response = await client.post(
        f"/api/projects/{project_id}/sessions",
        json={"title": "Resume Session", "language": "en"},
    )
    assert response.status_code == 200
    session_id = response.json()["session"]["id"]

    response = await client.post(f"/api/sessions/{session_id}/start")
    assert response.status_code == 200
    assert response.json()["status"] == "running"

    response = await client.post(f"/api/sessions/{session_id}/stop")
    assert response.status_code == 200

    response = await client.post(f"/api/sessions/{session_id}/resume")
    assert response.status_code == 200
    assert response.json()["status"] == "running"
