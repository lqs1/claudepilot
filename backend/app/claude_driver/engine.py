"""Async driver for the Claude Code CLI subprocess."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import uuid
from pathlib import Path
from typing import Any, Callable

from app.claude_driver.builder import ClaudeCommandBuilder
from app.claude_driver.events import (
    AssistantEvent,
    ClaudeEvent,
    ErrorEvent,
    InitEvent,
    Question,
    RawOutputEvent,
    ResultEvent,
    StreamEventParser,
    ToolResult,
    ToolUse,
)

logger = logging.getLogger(__name__)

EventHandler = Callable[[ClaudeEvent], None]


class ClaudeEngine:
    """Manages a single Claude Code CLI session."""

    def __init__(
        self,
        project_path: Path,
        session_id: str | None = None,
        *,
        model: str | None = None,
        permission_mode: str = "acceptEdits",
        append_system_prompt: str | None = None,
        effort: str | None = None,
        max_turns: int | None = None,
        tools_enabled: bool = True,
        mcp_servers: list[dict[str, Any]] | None = None,
        chrome_enabled: bool = False,
        resume: bool = False,
    ) -> None:
        self.project_path = Path(project_path)
        self.session_id = session_id or str(uuid.uuid4())
        self.model = model
        self.permission_mode = permission_mode
        self.append_system_prompt = append_system_prompt
        self.effort = effort
        self.max_turns = max_turns
        self.tools_enabled = tools_enabled
        self.mcp_servers = mcp_servers or []
        self.chrome_enabled = chrome_enabled
        self.resume = resume

        self._process: asyncio.subprocess.Process | None = None
        self._parser = StreamEventParser()
        self._handlers: list[EventHandler] = []
        self._status = "stopped"
        self._lock = asyncio.Lock()
        self._read_task: asyncio.Task[None] | None = None
        self._stderr_task: asyncio.Task[None] | None = None
        self._exit_callback: Callable[[], None] | None = None

    @property
    def status(self) -> str:
        return self._status

    def add_handler(self, handler: EventHandler) -> None:
        """Register an event handler."""
        self._handlers.append(handler)

    def remove_handler(self, handler: EventHandler) -> None:
        """Unregister an event handler."""
        if handler in self._handlers:
            self._handlers.remove(handler)

    async def start(self) -> None:
        """Spawn the Claude CLI process."""
        async with self._lock:
            if self._process is not None:
                raise RuntimeError("Engine is already running")

            args = ClaudeCommandBuilder.build_args(
                project_path=self.project_path,
                session_id=self.session_id,
                resume=self.resume,
                model=self.model,
                permission_mode=self.permission_mode,
                append_system_prompt=self.append_system_prompt,
                effort=self.effort,
                max_turns=self.max_turns,
                tools_enabled=self.tools_enabled,
                mcp_servers=self.mcp_servers,
                chrome_enabled=self.chrome_enabled,
            )
            env = ClaudeCommandBuilder.build_environment()

            logger.info("Starting Claude CLI: claude %s", " ".join(args))
            self._process = await asyncio.create_subprocess_exec(
                "claude",
                *args,
                cwd=self.project_path,
                env=env,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._status = "running"

        self._read_task = asyncio.create_task(self._read_stream())
        self._stderr_task = asyncio.create_task(self._read_stderr())

    async def send_message(self, content: str) -> None:
        """Send a user message to the CLI."""
        await self._send(
            {"type": "user", "message": {"role": "user", "content": content}}
        )

    async def send_tool_result(
        self, tool_use_id: str, content: str, *, is_error: bool = False
    ) -> None:
        """Send a tool result to the CLI."""
        message = {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": content,
                    "is_error": is_error,
                }
            ],
        }
        await self._send({"type": "user", "message": message})

    async def answer_question(
        self, tool_use_id: str, questions: list[Question]
    ) -> None:
        """Answer an AskUserQuestion tool."""
        answers = []
        for question in questions:
            answer: dict[str, Any] = {"question": question.question}
            if question.options:
                answer["selected_options"] = [opt["value"] for opt in question.options]
            answers.append(answer)
        await self.send_tool_result(tool_use_id, json.dumps(answers))

    async def stop(self) -> None:
        """Stop the CLI process gracefully."""
        async with self._lock:
            if self._process is None:
                return

            self._status = "stopped"
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except TimeoutError:
                logger.warning("Claude CLI did not terminate, killing")
                self._process.kill()
                await self._process.wait()
            except ProcessLookupError:
                pass
            finally:
                self._process = None

        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._read_task
        if self._stderr_task and not self._stderr_task.done():
            self._stderr_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._stderr_task

    async def _send(self, payload: dict[str, Any]) -> None:
        if self._process is None or self._process.stdin is None:
            raise RuntimeError("Engine is not running")
        line = json.dumps(payload) + "\n"
        logger.debug("STDIN >>> %s", line.strip())
        self._process.stdin.write(line.encode("utf-8"))
        await self._process.stdin.drain()

    async def _read_stream(self) -> None:
        if self._process is None or self._process.stdout is None:
            return

        try:
            while True:
                line_bytes = await self._process.stdout.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode("utf-8", errors="replace")
                logger.debug("STDOUT <<< %s", line.strip())
                event = self._parser.parse_line(line)
                if event is not None:
                    self._emit(event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error reading Claude CLI stdout")
            self._emit(ErrorEvent(type="error", message=str(exc)))
        finally:
            await self._on_exit()

    async def _read_stderr(self) -> None:
        if self._process is None or self._process.stderr is None:
            return

        try:
            while True:
                line_bytes = await self._process.stderr.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode("utf-8", errors="replace")
                logger.warning("STDERR <<< %s", line.strip())
                self._emit(
                    RawOutputEvent(type="raw_output", stream="stderr", content=line)
                )
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            logger.exception("Error reading Claude CLI stderr")

    async def _on_exit(self) -> None:
        return_code = None
        if self._process is not None:
            return_code = self._process.returncode
        self._status = "stopped" if return_code in (0, None) else "error"
        logger.info("Claude CLI exited with code %s", return_code)
        self._notify_exit_callback()

    def _notify_exit_callback(self) -> None:
        if self._exit_callback is not None:
            try:
                self._exit_callback()
            except Exception:  # noqa: BLE001
                logger.exception("Engine exit callback failed")

    def notify_exit(self, callback: Callable[[], None]) -> None:
        """Register a callback invoked when the engine process exits."""
        self._exit_callback = callback

    def _emit(self, event: ClaudeEvent) -> None:
        for handler in self._handlers:
            try:
                handler(event)
            except Exception:  # noqa: BLE001
                logger.exception("Event handler failed")


__all__ = [
    "ClaudeEngine",
    "EventHandler",
    "AssistantEvent",
    "ErrorEvent",
    "InitEvent",
    "Question",
    "ResultEvent",
    "ToolResult",
    "ToolUse",
]
