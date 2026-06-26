"""Manage active Claude CLI sessions."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

from app.claude_driver import (
    AssistantEvent,
    ClaudeEngine,
    ClaudeEvent,
    ErrorEvent,
    InitEvent,
    PlanEvent,
    ResultEvent,
)
from app.claude_driver.events import PermissionRequestEvent, RawOutputEvent, StatusEvent

logger = logging.getLogger(__name__)

EventCallback = Callable[[str, dict[str, Any]], None]


class ClaudeSessionManager:
    """Keeps track of running Claude CLI sessions and broadcasts their events."""

    def __init__(self) -> None:
        self._engines: dict[str, ClaudeEngine] = {}
        self._callbacks: list[EventCallback] = []
        self._persist_callbacks: dict[str, EventCallback] = {}

    def add_callback(self, callback: EventCallback) -> None:
        """Register a callback receiving (session_id, event_payload)."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def remove_callback(self, callback: EventCallback) -> None:
        """Unregister a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def register_persist_callback(
        self, session_id: str, callback: EventCallback
    ) -> None:
        """Register a persist callback for a session, replacing any existing one."""
        self.unregister_persist_callback(session_id)
        self._persist_callbacks[session_id] = callback
        self.add_callback(callback)

    def unregister_persist_callback(self, session_id: str) -> None:
        """Remove the persist callback for a session."""
        old = self._persist_callbacks.pop(session_id, None)
        if old is not None:
            self.remove_callback(old)

    def _broadcast_status(self, session_id: str, status: str) -> None:
        """Broadcast a status event to all registered callbacks."""
        for callback in self._callbacks:
            try:
                callback(session_id, {"type": "status", "status": status})
            except Exception:  # noqa: BLE001
                logger.exception("Status event callback failed")

    async def start_session(
        self,
        session_id: str,
        project_path: Path,
        *,
        language: str = "zh",
        model: str | None = None,
        permission_mode: str = "acceptEdits",
        effort: str | None = None,
        max_turns: int | None = None,
        tools_enabled: bool = True,
        mcp_servers: list[dict[str, Any]] | None = None,
        initial_message: str | None = None,
        resume: bool = False,
    ) -> ClaudeEngine:
        """Start a new Claude CLI session."""
        existing = self._engines.pop(session_id, None)
        if existing is not None:
            await existing.stop()
            logger.warning("Replaced stale engine for session %s", session_id)

        system_prompt = self._system_prompt_for_language(language)
        engine = ClaudeEngine(
            project_path=project_path,
            session_id=session_id,
            model=model,
            permission_mode=permission_mode,
            append_system_prompt=system_prompt,
            effort=effort,
            max_turns=max_turns,
            tools_enabled=tools_enabled,
            mcp_servers=mcp_servers or [],
            resume=resume,
        )
        engine.add_handler(lambda event: self._on_event(session_id, event))

        def _remove_engine() -> None:
            self._engines.pop(session_id, None)

        engine.notify_exit(_remove_engine)
        self._engines[session_id] = engine
        await engine.start()
        self._broadcast_status(session_id, "idle")
        if initial_message:
            await engine.send_message(initial_message)
        logger.info("Started Claude session %s", session_id)
        return engine

    async def send_message(self, session_id: str, content: str) -> None:
        """Send a user message to a running session."""
        engine = self._get_engine(session_id)
        self._broadcast_status(session_id, "thinking")
        await engine.send_message(content)

    async def answer_question(
        self, session_id: str, tool_use_id: str, answers: list[dict[str, Any]]
    ) -> None:
        """Answer an AskUserQuestion tool call."""
        engine = self._get_engine(session_id)
        from app.claude_driver.events import Question

        questions = []
        for answer in answers:
            questions.append(
                Question(
                    question=answer.get("question", ""),
                    options=answer.get("options", []),
                )
            )
        await engine.answer_question(tool_use_id, questions)

    async def respond_permission(
        self, session_id: str, tool_use_id: str, allowed: bool
    ) -> None:
        """Respond to a permission request."""
        engine = self._get_engine(session_id)
        content = "allow" if allowed else "deny"
        await engine.send_tool_result(tool_use_id, content)

    async def send_plan_feedback(
        self, session_id: str, action: str, message: str
    ) -> None:
        """Send plan feedback to a running session."""
        engine = self._get_engine(session_id)
        if action == "approve":
            await engine.send_message("y")
        elif action == "reject":
            await engine.send_message("n")
        else:
            await engine.send_message(message)

    async def stop_session(self, session_id: str) -> None:
        """Stop a running session."""
        engine = self._engines.pop(session_id, None)
        if engine is not None:
            await engine.stop()
            self._broadcast_status(session_id, "idle")
            logger.info("Stopped Claude session %s", session_id)

    def get_status(self, session_id: str) -> str:
        """Return the status of a session."""
        engine = self._engines.get(session_id)
        return engine.status if engine else "stopped"

    def _get_engine(self, session_id: str) -> ClaudeEngine:
        engine = self._engines.get(session_id)
        if engine is None:
            raise RuntimeError(f"Session {session_id} is not running")
        return engine

    def _on_event(self, session_id: str, event: ClaudeEvent) -> None:
        if isinstance(event, AssistantEvent):
            status = "writing" if event.text_deltas else "thinking"
            self._broadcast_status(session_id, status)
        elif isinstance(event, ErrorEvent):
            self._broadcast_status(session_id, "error")

        payload = self._event_to_payload(event)
        if payload is None:
            return
        for callback in self._callbacks:
            try:
                callback(session_id, payload)
            except Exception:  # noqa: BLE001
                logger.exception("Session event callback failed")

    def _event_to_payload(self, event: ClaudeEvent) -> dict[str, Any] | None:
        if isinstance(event, InitEvent):
            return {"type": "init", "session_id": event.session_id}
        if isinstance(event, StatusEvent):
            return {"type": "status", "status": event.status}
        if isinstance(event, AssistantEvent):
            return {
                "type": "assistant",
                "message_id": event.message_id,
                "text": "".join(delta.text for delta in event.text_deltas),
                "tool_uses": [
                    {"id": t.id, "name": t.name, "input": t.input}
                    for t in event.tool_uses
                ],
                "usage": event.usage,
            }
        if isinstance(event, ResultEvent):
            return {
                "type": "result",
                "result": event.result,
                "is_error": event.is_error,
            }
        if isinstance(event, ErrorEvent):
            return {"type": "error", "message": event.message}
        if isinstance(event, PermissionRequestEvent):
            return {
                "type": "permission_request",
                "tool_use_id": event.tool_use_id,
                "tool": event.tool,
                "operation": event.operation,
                "reason": event.reason,
            }
        if isinstance(event, PlanEvent):
            return {
                "type": "plan",
                "plan": event.plan,
                "plan_mode": event.plan_mode,
            }
        if isinstance(event, RawOutputEvent):
            return {
                "type": "raw_output",
                "stream": event.stream,
                "content": event.content,
            }
        return None

    @staticmethod
    def _system_prompt_for_language(language: str) -> str:
        if language == "zh":
            return "请用中文回答。生成的代码注释和文档默认使用中文。"
        return "Please respond in English. Code comments and docs should be in English by default."


# Global singleton for the application process.
session_manager = ClaudeSessionManager()
