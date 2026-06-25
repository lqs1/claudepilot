"""Tests for the Claude CLI command builder."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.claude_driver.builder import ClaudeCommandBuilder


@pytest.fixture
def builder() -> ClaudeCommandBuilder:
    """Provide a command builder instance."""
    return ClaudeCommandBuilder()


class TestCommandBuilderArgs:
    """Unit tests for ClaudeCommandBuilder.build_args."""

    def test_minimal_args(self) -> None:
        """A minimal build should include required stream-json flags."""
        args = ClaudeCommandBuilder.build_args(
            project_path=Path("/tmp"),
            session_id="test-session",
        )
        assert "--print" in args
        assert "--session-id" in args
        assert "test-session" in args
        assert "--input-format" in args
        assert "stream-json" in args
        assert "--output-format" in args
        assert "--verbose" in args
        assert "--no-chrome" in args

    def test_model_argument(self) -> None:
        """Model is passed through when provided."""
        args = ClaudeCommandBuilder.build_args(
            project_path=Path("/tmp"),
            session_id="s1",
            model="claude-opus-4",
        )
        idx = args.index("--model")
        assert args[idx + 1] == "claude-opus-4"

    def test_permission_mode_argument(self) -> None:
        """Permission mode defaults to acceptEdits."""
        args = ClaudeCommandBuilder.build_args(
            project_path=Path("/tmp"),
            session_id="s1",
        )
        idx = args.index("--permission-mode")
        assert args[idx + 1] == "acceptEdits"

    def test_effort_argument(self) -> None:
        """Effort is included when provided."""
        args = ClaudeCommandBuilder.build_args(
            project_path=Path("/tmp"),
            session_id="s1",
            effort="high",
        )
        idx = args.index("--effort")
        assert args[idx + 1] == "high"

    def test_max_turns_zero_is_ignored(self) -> None:
        """Zero max turns should not be passed to the CLI (means unlimited)."""
        args = ClaudeCommandBuilder.build_args(
            project_path=Path("/tmp"),
            session_id="s1",
            max_turns=0,
        )
        assert "--max-turns" not in args

    def test_resume_argument(self) -> None:
        """Resume uses --resume with the session id."""
        args = ClaudeCommandBuilder.build_args(
            project_path=Path("/tmp"),
            session_id="s1",
            resume=True,
        )
        idx = args.index("--resume")
        assert args[idx + 1] == "s1"
        assert "--session-id" not in args

    def test_tools_enabled_argument(self) -> None:
        """Tools enabled flag maps to allowed/disallowed tool lists."""
        args = ClaudeCommandBuilder.build_args(
            project_path=Path("/tmp"),
            session_id="s1",
            tools_enabled=True,
        )
        # When tools are enabled we currently do not restrict the list.
        assert "--allowedTools" not in args
        assert "--disallowedTools" not in args

    def test_tools_disabled_argument(self) -> None:
        """Disabling tools passes an empty allowed list."""
        args = ClaudeCommandBuilder.build_args(
            project_path=Path("/tmp"),
            session_id="s1",
            tools_enabled=False,
        )
        idx = args.index("--allowedTools")
        assert args[idx + 1] == ""

    def test_append_system_prompt_argument(self) -> None:
        """Append system prompt is forwarded when provided."""
        args = ClaudeCommandBuilder.build_args(
            project_path=Path("/tmp"),
            session_id="s1",
            append_system_prompt="reply in Chinese",
        )
        idx = args.index("--append-system-prompt")
        assert args[idx + 1] == "reply in Chinese"

    def test_build_environment_unsets_claudecode(self) -> None:
        """The environment removes CLAUDECODE to avoid nested session issues."""
        env = ClaudeCommandBuilder.build_environment({"CLAUDECODE": "1"})
        assert "CLAUDECODE" not in env

    def test_build_environment_force_color(self) -> None:
        """FORCE_COLOR is set in the environment."""
        env = ClaudeCommandBuilder.build_environment()
        assert env["FORCE_COLOR"] == "1"
