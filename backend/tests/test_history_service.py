"""Tests for HistoryService: reading and editing the CLI jsonl history.

These build synthetic jsonl files that mirror the CLI's real layout:
   ~/.claude/projects/<encoded-path>/<session-id>.jsonl
and verify (1) turns aggregate correctly, (2) paired deletion keeps the
parentUuid chain intact so the CLI can still resume.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import app.services.history_service as history_module
from app.services.history_service import HistoryService


def _row(
    type_: str,
    uuid: str | None = None,
    parent: str | None = None,
    *,
    role: str | None = None,
    content: Any = None,
    is_sidechain: bool = False,
    timestamp: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a minimal CLI history row."""
    row: dict[str, Any] = {"type": type_, "timestamp": timestamp}
    if uuid is not None:
        row["uuid"] = uuid
    if parent is not None:
        row["parentUuid"] = parent
    if is_sidechain:
        row["isSidechain"] = True
    if role is not None or content is not None:
        row["message"] = {"role": role or type_, "content": content}
    if extra:
        row.update(extra)
    return row


def _write_session(
    history_dir: Path, project_path: str, sid: str, rows: list[dict]
) -> Path:
    """Write rows into the CLI-shaped path and return the file path."""
    encoded = project_path.replace("/", "-")
    folder = history_dir / encoded
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{sid}.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for r in rows:
            handle.write(json.dumps(r))
            handle.write("\n")
    return path


@pytest.fixture
def history_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point CLAUDE_HISTORY_DIR at a temp dir for the duration of the test."""
    d = tmp_path / "projects"
    d.mkdir()
    monkeypatch.setattr(history_module, "CLAUDE_HISTORY_DIR", d)
    return d


def _build_two_turn_session() -> list[dict]:
    """A session with two text turns (the PONG-style layout)."""
    return [
        _row("queue-operation"),
        _row("user", "u1", content="ping", timestamp="t1"),
        _row("attachment", "a1", "u1"),
        _row("assistant", "s1", "a1", content=[{"type": "thinking"}]),
        _row("assistant", "s2", "s1", content=[{"type": "text", "text": "pong"}]),
        _row("user", "u2", "s2", content="hello again", timestamp="t2"),
        _row("assistant", "s3", "u2", content=[{"type": "text", "text": "hi"}]),
        _row("last-prompt"),
    ]


class TestListTurns:
    def test_text_turns_aggregate(self, history_dir: Path) -> None:
        rows = _build_two_turn_session()
        _write_session(history_dir, "/proj/p1", "sid1", rows)

        svc = HistoryService(Path("/proj/p1"), "sid1")
        messages = svc.list_messages()

        # 2 turns -> 4 messages (user + assistant each)
        assert [m["role"] for m in messages] == [
            "user",
            "assistant",
            "user",
            "assistant",
        ]
        assert messages[0]["content"] == "ping"
        assert messages[1]["content"] == "pong"
        assert messages[2]["content"] == "hello again"
        assert messages[3]["content"] == "hi"
        # The assistant and its prompt share the turn uuid.
        assert messages[0]["uuid"] == messages[1]["uuid"] == "u1"
        assert messages[2]["uuid"] == messages[3]["uuid"] == "u2"

    def test_missing_file_returns_empty(self, history_dir: Path) -> None:
        svc = HistoryService(Path("/proj/none"), "nope")
        assert svc.list_messages() == []
        assert svc.exists() is False

    def test_tool_calls_captured(self, history_dir: Path) -> None:
        rows = [
            _row("user", "u1", content="read the file", timestamp="t1"),
            _row(
                "assistant",
                "s1",
                "u1",
                content=[
                    {
                        "type": "tool_use",
                        "id": "tu1",
                        "name": "Read",
                        "input": {"path": "a"},
                    },
                    {"type": "text", "text": "done"},
                ],
            ),
            _row(
                "user",
                "u2",
                "s1",
                content=[{"type": "tool_result", "tool_use_id": "tu1"}],
            ),
        ]
        _write_session(history_dir, "/proj/t", "sid", rows)

        messages = HistoryService(Path("/proj/t"), "sid").list_messages()
        # one user prompt + one assistant reply (with tool_uses)
        assert len(messages) == 2
        assert messages[1]["tool_uses"] == [
            {"id": "tu1", "name": "Read", "input": {"path": "a"}}
        ]
        assert messages[1]["content"] == "done"


class TestPathEncoding:
    def test_encode(self) -> None:
        from app.services.history_service import encode_project_path

        # Slashes and dots both become dashes (matches real CLI layout).
        assert encode_project_path(Path("/Users/qslu/p")) == "-Users-qslu-p"
        # Dots are encoded like slashes. The expectation is derived from the
        # resolved path so the test is independent of OS-specific symlinks
        # (e.g. macOS resolves /var -> /private/var).
        dotted = Path("/var/folders/x/T/tmp.abc")
        expected = str(dotted.resolve()).replace("/", "-").replace(".", "-")
        assert encode_project_path(dotted) == expected


class TestDeleteTurn:
    def test_delete_first_turn_repairs_chain(self, history_dir: Path) -> None:
        rows = _build_two_turn_session()
        path = _write_session(history_dir, "/proj/p1", "sid1", rows)

        svc = HistoryService(Path("/proj/p1"), "sid1")
        assert svc.delete_turn("u1") is True

        kept = [
            json.loads(line) for line in path.read_text().splitlines() if line.strip()
        ]
        kept_uuids = {r.get("uuid") for r in kept}
        # u1 and its assistant/attachment are gone; u2 reply chain survives.
        assert "u1" not in kept_uuids
        assert "a1" not in kept_uuids
        assert "s1" not in kept_uuids
        assert "s2" not in kept_uuids
        assert {"u2", "s3"}.issubset(kept_uuids)

        # The surviving top-level prompt u2 was parented on s2 (now deleted);
        # it must be reparented onto None (nothing kept before the segment).
        u2 = next(r for r in kept if r.get("uuid") == "u2")
        assert u2["parentUuid"] is None or u2.get("parentUuid") in (None, "")

    def test_delete_second_turn_keeps_first(self, history_dir: Path) -> None:
        rows = _build_two_turn_session()
        path = _write_session(history_dir, "/proj/p1", "sid1", rows)

        svc = HistoryService(Path("/proj/p1"), "sid1")
        assert svc.delete_turn("u2") is True

        kept = [
            json.loads(line) for line in path.read_text().splitlines() if line.strip()
        ]
        kept_uuids = {r.get("uuid") for r in kept}
        assert {"u1", "s2"}.issubset(kept_uuids)
        assert "u2" not in kept_uuids
        assert "s3" not in kept_uuids

    def test_delete_unknown_turn_returns_false(self, history_dir: Path) -> None:
        _write_session(history_dir, "/proj/p1", "sid1", _build_two_turn_session())
        svc = HistoryService(Path("/proj/p1"), "sid1")
        assert svc.delete_turn("does-not-exist") is False

    def test_delete_only_turn_is_safe(self, history_dir: Path) -> None:
        rows = [
            _row("user", "u1", content="ping", timestamp="t1"),
            _row("assistant", "s1", "u1", content=[{"type": "text", "text": "pong"}]),
            _row("last-prompt"),
        ]
        path = _write_session(history_dir, "/proj/p1", "sid1", rows)

        svc = HistoryService(Path("/proj/p1"), "sid1")
        assert svc.delete_turn("u1") is True

        kept = [
            json.loads(line) for line in path.read_text().splitlines() if line.strip()
        ]
        # Only metadata rows remain; the file is still valid jsonl.
        assert all(
            r.get("uuid") is None or r.get("type") not in ("user", "assistant")
            for r in kept
        )
        # No message turns left -> nothing to display.
        assert HistoryService(Path("/proj/p1"), "sid1").list_messages() == []
