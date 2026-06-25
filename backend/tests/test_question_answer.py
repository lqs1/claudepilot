"""Tests for AskUserQuestion answer formatting."""

from __future__ import annotations

import json

import pytest

from app.claude_driver.events import Question
from app.claude_driver.engine import ClaudeEngine


class TestAnswerQuestionFormatting:
    """Unit tests for answer_question payload format."""

    @pytest.mark.asyncio
    async def test_answer_question_sends_json(self, tmp_path: str) -> None:
        """Answers are sent as a JSON string inside the tool_result content."""
        engine = ClaudeEngine(project_path=tmp_path)
        sent_payloads: list[dict] = []

        async def fake_send(payload: dict) -> None:
            sent_payloads.append(payload)

        engine._send = fake_send  # type: ignore[assignment]

        questions = [
            Question(
                question="Proceed?",
                header="Confirm",
                options=[{"value": "yes", "label": "Yes"}],
            )
        ]
        await engine.answer_question("toolu_123", questions)

        assert len(sent_payloads) == 1
        message = sent_payloads[0]["message"]
        assert message["role"] == "user"
        content = message["content"][0]
        assert content["type"] == "tool_result"
        assert content["tool_use_id"] == "toolu_123"

        parsed = json.loads(content["content"])
        assert len(parsed) == 1
        assert parsed[0]["question"] == "Proceed?"
        assert parsed[0]["selected_options"] == ["yes"]
