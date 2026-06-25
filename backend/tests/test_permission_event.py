"""Tests for permission request event parsing."""

from __future__ import annotations

import json

from app.claude_driver.events import PermissionRequestEvent, StreamEventParser
from app.services.claude_manager import ClaudeSessionManager


class TestPermissionRequestParsing:
    """Unit tests for permission request events."""

    def test_parse_includes_tool_use_id(self) -> None:
        """The parser extracts the tool_use_id from permission_request events."""
        parser = StreamEventParser()
        line = json.dumps(
            {
                "type": "permission_request",
                "user_input": {
                    "tool": "Bash",
                    "operation": "ls -la",
                    "reason": "List files",
                    "tool_use_id": "toolu_abc123",
                },
            }
        )
        event = parser.parse_line(line)
        assert isinstance(event, PermissionRequestEvent)
        assert event.tool_use_id == "toolu_abc123"

    def test_event_to_payload_includes_tool_use_id(self) -> None:
        """The payload forwarded to the UI includes the tool_use_id."""
        manager = ClaudeSessionManager()
        event = PermissionRequestEvent(
            type="permission_request",
            tool="Bash",
            operation="ls -la",
            reason="List files",
            tool_use_id="toolu_abc123",
        )
        payload = manager._event_to_payload(event)
        assert payload is not None
        assert payload["tool_use_id"] == "toolu_abc123"
