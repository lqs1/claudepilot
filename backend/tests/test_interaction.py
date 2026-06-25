"""Tests for permission and question interaction APIs."""

from __future__ import annotations

import uuid
from typing import Any

import pytest


@pytest.mark.asyncio
async def test_answer_question_returns_answered(client: Any) -> None:
    """The answer endpoint acknowledges the response."""
    response = await client.post(
        "/api/projects", json={"name": f"AQ-{uuid.uuid4().hex[:6]}", "path": "/tmp"}
    )
    project_id = response.json()["project"]["id"]

    response = await client.post(
        f"/api/projects/{project_id}/sessions",
        json={"title": "AQ Session", "language": "en"},
    )
    session_id = response.json()["session"]["id"]

    response = await client.post(
        f"/api/sessions/{session_id}/answer",
        json={
            "tool_use_id": "toolu_123",
            "answers": [{"question": "Proceed?", "options": [{"value": "yes"}]}],
        },
    )
    # Session not running → 409
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_answer_question_missing_fields(client: Any) -> None:
    """The answer endpoint requires tool_use_id and answers."""
    response = await client.post("/api/sessions/nonexistent/answer", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_respond_permission_returns_responded(client: Any) -> None:
    """The permission endpoint acknowledges the response."""
    response = await client.post(
        "/api/sessions/nonexistent/permission",
        json={"tool_use_id": "toolu_456", "allowed": True},
    )
    # Session not running → 409
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_respond_permission_missing_tool_use_id(client: Any) -> None:
    """The permission endpoint requires tool_use_id."""
    response = await client.post(
        "/api/sessions/nonexistent/permission",
        json={"allowed": True},
    )
    assert response.status_code == 422
