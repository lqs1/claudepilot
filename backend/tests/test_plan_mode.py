"""Tests for plan event parsing and plan feedback API."""

from __future__ import annotations

import json

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.claude_driver.events import (
    PlanEvent,
    StreamEventParser,
)
from app.database import Base, engine
from app.main import app


class TestPlanEventParsing:
    """Unit tests for plan event parsing in StreamEventParser."""

    @pytest.fixture
    def parser(self) -> StreamEventParser:
        return StreamEventParser()

    def test_parse_plan_enter_event(self, parser: StreamEventParser) -> None:
        line = json.dumps({"type": "plan", "plan": "", "plan_mode": "enter"})
        event = parser.parse_line(line)
        assert isinstance(event, PlanEvent)
        assert event.type == "plan"
        assert event.plan_mode == "enter"
        assert event.plan == ""

    def test_parse_plan_exit_event(self, parser: StreamEventParser) -> None:
        line = json.dumps({"type": "plan", "plan": "", "plan_mode": "exit"})
        event = parser.parse_line(line)
        assert isinstance(event, PlanEvent)
        assert event.plan_mode == "exit"

    def test_parse_plan_text_event(self, parser: StreamEventParser) -> None:
        line = json.dumps(
            {
                "type": "plan",
                "plan": "1. Analyze codebase\n2. Write tests",
                "plan_mode": "text",
            }
        )
        event = parser.parse_line(line)
        assert isinstance(event, PlanEvent)
        assert event.plan_mode == "text"
        assert event.plan == "1. Analyze codebase\n2. Write tests"

    def test_parse_plan_default_mode(self, parser: StreamEventParser) -> None:
        line = json.dumps({"type": "plan", "plan": "Some plan text"})
        event = parser.parse_line(line)
        assert isinstance(event, PlanEvent)
        assert event.plan_mode == "text"
        assert event.plan == "Some plan text"

    def test_parse_plan_event_to_payload(self, parser: StreamEventParser) -> None:
        from app.services.claude_manager import ClaudeSessionManager

        line = json.dumps(
            {"type": "plan", "plan": "1. Step one\n2. Step two", "plan_mode": "text"}
        )
        event = parser.parse_line(line)
        assert isinstance(event, PlanEvent)

        manager = ClaudeSessionManager()
        payload = manager._event_to_payload(event)
        assert payload is not None
        assert payload["type"] == "plan"
        assert payload["plan"] == "1. Step one\n2. Step two"
        assert payload["plan_mode"] == "text"


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


class TestPlanFeedbackAPI:
    """Integration tests for the plan feedback API endpoint."""

    @pytest.mark.asyncio
    async def test_plan_feedback_invalid_action(self, client: AsyncClient) -> None:
        """Invalid action should return 422."""
        response = await client.post(
            "/api/sessions/test-session/plan-feedback", json={"action": "invalid"}
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_plan_feedback_session_not_running(self, client: AsyncClient) -> None:
        """Feedback to a non-running session should return 409."""
        response = await client.post(
            "/api/sessions/nonexistent-session/plan-feedback",
            json={"action": "approve", "message": ""},
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_plan_feedback_approve(self, client: AsyncClient) -> None:
        """Approve action should be accepted (session not running returns 409)."""
        response = await client.post(
            "/api/sessions/test-session/plan-feedback",
            json={"action": "approve", "message": ""},
        )
        # Session is not running, so we expect 409
        assert response.status_code == 409
        assert "not running" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_plan_feedback_reject(self, client: AsyncClient) -> None:
        """Reject action should be accepted (session not running returns 409)."""
        response = await client.post(
            "/api/sessions/test-session/plan-feedback",
            json={"action": "reject", "message": ""},
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_plan_feedback_with_message(self, client: AsyncClient) -> None:
        """Feedback action with message should be accepted (session not running returns 409)."""
        response = await client.post(
            "/api/sessions/test-session/plan-feedback",
            json={"action": "feedback", "message": "Please add more tests"},
        )
        assert response.status_code == 409


class TestClaudeManagerPlanFeedback:
    """Unit tests for ClaudeSessionManager.send_plan_feedback."""

    def test_send_plan_feedback_approve(self) -> None:
        """Approve sends 'y' message to engine."""
        from unittest.mock import AsyncMock, MagicMock
        from app.services.claude_manager import ClaudeSessionManager

        manager = ClaudeSessionManager()
        mock_engine = MagicMock()
        mock_engine.send_message = AsyncMock()
        manager._engines["test-session"] = mock_engine

        import asyncio

        asyncio.run(manager.send_plan_feedback("test-session", "approve", ""))

        mock_engine.send_message.assert_awaited_once_with("y")

    def test_send_plan_feedback_reject(self) -> None:
        """Reject sends 'n' message to engine."""
        from unittest.mock import AsyncMock, MagicMock
        from app.services.claude_manager import ClaudeSessionManager

        manager = ClaudeSessionManager()
        mock_engine = MagicMock()
        mock_engine.send_message = AsyncMock()
        manager._engines["test-session"] = mock_engine

        import asyncio

        asyncio.run(manager.send_plan_feedback("test-session", "reject", ""))

        mock_engine.send_message.assert_awaited_once_with("n")

    def test_send_plan_feedback_custom(self) -> None:
        """Feedback sends custom message to engine."""
        from unittest.mock import AsyncMock, MagicMock
        from app.services.claude_manager import ClaudeSessionManager

        manager = ClaudeSessionManager()
        mock_engine = MagicMock()
        mock_engine.send_message = AsyncMock()
        manager._engines["test-session"] = mock_engine

        import asyncio

        asyncio.run(
            manager.send_plan_feedback("test-session", "feedback", "Add more tests")
        )

        mock_engine.send_message.assert_awaited_once_with("Add more tests")

    def test_send_plan_feedback_no_session(self) -> None:
        """Feedback to non-existent session raises RuntimeError."""
        from app.services.claude_manager import ClaudeSessionManager

        manager = ClaudeSessionManager()

        import asyncio

        with pytest.raises(RuntimeError, match="not running"):
            asyncio.run(manager.send_plan_feedback("nonexistent", "approve", ""))
