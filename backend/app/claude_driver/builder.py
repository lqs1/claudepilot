"""Build command-line arguments and environment for Claude Code CLI."""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path
from typing import Any


class ClaudeCommandBuilder:
    """Construct the arguments and environment used to spawn `claude`."""

    @staticmethod
    def build_args(
        *,
        project_path: Path,
        session_id: str,
        resume: bool = False,
        model: str | None = None,
        permission_mode: str = "acceptEdits",
        append_system_prompt: str | None = None,
        max_turns: int | None = None,
        mcp_servers: list[dict[str, Any]] | None = None,
        chrome_enabled: bool = False,
    ) -> list[str]:
        """Return the CLI argument list for `claude`."""
        args = ["--print"]

        if model:
            args.extend(["--model", model])

        args.extend(["--permission-mode", permission_mode])

        if resume:
            args.extend(["--resume", session_id])
        else:
            args.extend(["--session-id", session_id])

        if append_system_prompt:
            args.extend(["--append-system-prompt", append_system_prompt])

        if max_turns:
            args.extend(["--max-turns", str(max_turns)])

        args.extend(
            [
                "--input-format",
                "stream-json",
                "--output-format",
                "stream-json",
                "--verbose",
            ]
        )

        if mcp_servers:
            config_path = ClaudeCommandBuilder._write_mcp_config(mcp_servers)
            args.extend(["--mcp-config", config_path])

        args.append("--chrome" if chrome_enabled else "--no-chrome")

        return args

    @staticmethod
    def build_environment(env: dict[str, str] | None = None) -> dict[str, str]:
        """Return environment variables for the Claude CLI process."""
        environment = {**os.environ, **(env or {})}
        environment["FORCE_COLOR"] = "1"
        environment["ANTHROPIC_TELEMETRY"] = "false"
        # Prevent nested session errors when running inside a Claude Code terminal.
        environment.pop("CLAUDECODE", None)
        return environment

    @staticmethod
    def _write_mcp_config(servers: list[dict[str, Any]]) -> str:
        """Write a temporary MCP config file and return its path."""
        mcp_servers: dict[str, dict[str, Any]] = {}
        for server in servers:
            name = server["name"]
            config: dict[str, Any] = {"type": server["type"]}
            if server["type"] == "stdio":
                config["command"] = server["command"]
                if server.get("args"):
                    config["args"] = server["args"]
                if server.get("env"):
                    config["env"] = server["env"]
            elif server["type"] == "http":
                config["url"] = server["url"]
                if server.get("headers"):
                    config["headers"] = server["headers"]
            mcp_servers[name] = config

        temp_dir = Path(tempfile.gettempdir()) / "claudepilot-mcp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        config_path = temp_dir / f"mcp-{uuid.uuid4()}.json"
        config_path.write_text(
            __import__("json").dumps({"mcpServers": mcp_servers}, indent=2)
        )
        return str(config_path)
