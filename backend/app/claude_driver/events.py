"""Parse streaming JSON events emitted by Claude Code CLI."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TextDelta:
    text: str


@dataclass
class ToolUse:
    id: str
    name: str
    input: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    tool_use_id: str
    content: str
    is_error: bool = False


@dataclass
class Question:
    question: str
    header: str | None = None
    options: list[dict[str, str]] = field(default_factory=list)
    multi_select: bool = False


@dataclass
class PlanFeedback:
    action: str  # "approve", "reject", "feedback"
    message: str = ""


@dataclass
class ClaudeEvent:
    """Base class for parsed CLI events."""

    type: str


@dataclass
class PlanEvent(ClaudeEvent):
    plan: str
    plan_mode: str = "text"  # "enter", "exit", "text"


@dataclass
class InitEvent(ClaudeEvent):
    session_id: str | None = None


@dataclass
class StatusEvent(ClaudeEvent):
    status: str


@dataclass
class CompactionEvent(ClaudeEvent):
    summary: str


@dataclass
class AssistantEvent(ClaudeEvent):
    message_id: str | None = None
    text_deltas: list[TextDelta] = field(default_factory=list)
    tool_uses: list[ToolUse] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)


@dataclass
class UserEvent(ClaudeEvent):
    tool_results: list[ToolResult] = field(default_factory=list)


@dataclass
class ResultEvent(ClaudeEvent):
    result: str = ""
    is_error: bool = False
    errors: list[str] = field(default_factory=list)


@dataclass
class ErrorEvent(ClaudeEvent):
    message: str


@dataclass
class PermissionRequestEvent(ClaudeEvent):
    tool: str
    operation: str
    reason: str
    allow_once: bool = False
    allow_always: bool = False
    deny: bool = False


@dataclass
class RawOutputEvent(ClaudeEvent):
    stream: str  # "stdout" or "stderr"
    content: str


class StreamEventParser:
    """Parse line-delimited JSON events from Claude CLI stdout."""

    def __init__(self) -> None:
        self._last_text = ""
        self._current_tool: ToolUse | None = None
        self._partial_json = ""

    def parse_line(self, line: str) -> ClaudeEvent | None:
        """Parse a single line of output."""
        line = line.strip()
        if not line:
            return None

        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return RawOutputEvent(type="raw_output", stream="stdout", content=line)

        if not isinstance(data, dict):
            return RawOutputEvent(type="raw_output", stream="stdout", content=line)

        event_type = data.get("type")
        handler = getattr(self, f"_handle_{event_type}", self._handle_unknown)
        return handler(data)

    def _handle_system(self, data: dict[str, Any]) -> ClaudeEvent:
        subtype = data.get("subtype")
        if subtype == "init":
            return InitEvent(type="init", session_id=data.get("session_id"))
        if subtype == "status":
            return StatusEvent(type="status", status=data.get("status", ""))
        if subtype in ("compact", "compact_boundary"):
            return CompactionEvent(
                type="compaction", summary=data.get("content", "Context compacted")
            )
        return StatusEvent(type="status", status=subtype or "unknown")

    def _handle_assistant(self, data: dict[str, Any]) -> ClaudeEvent:
        message = data.get("message", {}) or {}
        content = message.get("content", []) or []
        usage = self._extract_usage(message.get("usage"))

        text_deltas: list[TextDelta] = []
        tool_uses: list[ToolUse] = []

        for block in content:
            if not isinstance(block, dict):
                continue
            block_type = block.get("type")
            if block_type == "text":
                text = block.get("text", "")
                if text:
                    text_deltas.append(TextDelta(text=text))
            elif block_type == "tool_use":
                tool_id = block.get("id") or block.get("tool_use_id")
                if tool_id:
                    tool_uses.append(
                        ToolUse(
                            id=tool_id,
                            name=block.get("name", "unknown"),
                            input=block.get("input") or {},
                        )
                    )

        return AssistantEvent(
            type="assistant",
            message_id=message.get("id"),
            text_deltas=text_deltas,
            tool_uses=tool_uses,
            usage=usage,
        )

    def _handle_user(self, data: dict[str, Any]) -> ClaudeEvent:
        message = data.get("message", {}) or {}
        content = message.get("content", []) or []
        tool_results: list[ToolResult] = []

        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_result":
                tool_results.append(
                    ToolResult(
                        tool_use_id=block.get("tool_use_id", ""),
                        content=block.get("content", ""),
                        is_error=bool(block.get("is_error")),
                    )
                )

        return UserEvent(type="user", tool_results=tool_results)

    def _handle_result(self, data: dict[str, Any]) -> ClaudeEvent:
        return ResultEvent(
            type="result",
            result=data.get("result", ""),
            is_error=bool(data.get("is_error")),
            errors=data.get("errors") or [],
        )

    def _handle_error(self, data: dict[str, Any]) -> ClaudeEvent:
        error = data.get("error", {}) or {}
        return ErrorEvent(type="error", message=error.get("message", "Unknown error"))

    def _handle_permission_request(self, data: dict[str, Any]) -> ClaudeEvent:
        user_input = data.get("user_input", {}) or {}
        return PermissionRequestEvent(
            type="permission_request",
            tool=user_input.get("tool", ""),
            operation=user_input.get("operation", ""),
            reason=user_input.get("reason", ""),
            allow_once=user_input.get("allow_once", False),
            allow_always=user_input.get("allow_always", False),
            deny=user_input.get("deny", False),
        )

    def _handle_plan(self, data: dict[str, Any]) -> ClaudeEvent:
        plan_mode = data.get("plan_mode", "text")
        return PlanEvent(
            type="plan",
            plan=data.get("plan", ""),
            plan_mode=plan_mode,
        )

    def _handle_stdout(self, data: dict[str, Any]) -> ClaudeEvent:
        return RawOutputEvent(
            type="raw_output", stream="stdout", content=data.get("content", "")
        )

    def _handle_stderr(self, data: dict[str, Any]) -> ClaudeEvent:
        return RawOutputEvent(
            type="raw_output", stream="stderr", content=data.get("content", "")
        )

    def _handle_unknown(self, data: dict[str, Any]) -> ClaudeEvent:
        return RawOutputEvent(
            type="raw_output", stream="stdout", content=json.dumps(data)
        )

    @staticmethod
    def _extract_usage(usage: Any) -> dict[str, int]:
        if not isinstance(usage, dict):
            return {}
        return {
            "input_tokens": usage.get("input_tokens", 0) or 0,
            "output_tokens": usage.get("output_tokens", 0) or 0,
            "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0)
            or 0,
            "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0) or 0,
        }
