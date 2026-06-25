"""Integration tests for the Claude CLI driver."""

from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path
from typing import Any

import pytest

from app.claude_driver import ClaudeEngine, InitEvent


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Provide a temporary project directory."""
    return tmp_path


@pytest.fixture(scope="session")
def claude_available() -> bool:
    """Check whether the Claude CLI is installed and authenticated."""
    return (
        shutil.which("claude") is not None
        and os.environ.get("SKIP_CLAUDE_TESTS") is None
    )


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(not shutil.which("claude"), reason="Claude CLI not installed")
async def test_engine_emits_init_event(temp_project: Path) -> None:
    """ClaudeEngine should emit an init event after starting."""
    events: list[Any] = []
    engine = ClaudeEngine(project_path=temp_project)
    engine.add_handler(events.append)

    await engine.start()
    try:
        # Claude CLI --print mode exits when stdin reaches EOF, so send an
        # initial message immediately to keep the session alive.
        await engine.send_message("Hello, please acknowledge with 'ready'.")
        await asyncio.wait_for(
            _wait_for_event(events, lambda e: isinstance(e, InitEvent), timeout=25.0),
            timeout=30.0,
        )
    finally:
        await engine.stop()

    assert any(isinstance(e, InitEvent) for e in events)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(not shutil.which("claude"), reason="Claude CLI not installed")
async def test_engine_receives_assistant_response(temp_project: Path) -> None:
    """Sending a message should produce an assistant response."""
    from app.claude_driver.events import AssistantEvent

    events: list[Any] = []
    engine = ClaudeEngine(project_path=temp_project, max_turns=1)
    engine.add_handler(events.append)

    await engine.start()
    try:
        # Claude CLI --print mode exits when stdin reaches EOF, so send an
        # initial message immediately to keep the session alive.
        await engine.send_message("Say exactly the word 'pong' and nothing else.")
        await asyncio.wait_for(
            _wait_for_event(events, lambda e: isinstance(e, InitEvent), timeout=25.0),
            timeout=30.0,
        )

        await asyncio.wait_for(
            _wait_for_event(
                events, lambda e: isinstance(e, AssistantEvent), timeout=55.0
            ),
            timeout=60.0,
        )
    finally:
        await engine.stop()

    assistant_events = [e for e in events if isinstance(e, AssistantEvent)]
    assert len(assistant_events) >= 1
    combined = "".join(
        delta.text for event in assistant_events for delta in event.text_deltas
    )
    assert "pong" in combined.lower()


async def _wait_for_event(
    events: list[Any], predicate: Any, timeout: float = 1.0
) -> Any:
    """Poll the event list until the predicate matches."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        for event in events:
            if predicate(event):
                return event
        await asyncio.sleep(0.1)
    raise TimeoutError("Predicate was not satisfied")
