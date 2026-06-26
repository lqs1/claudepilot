"""Tests for HistoryService.list_changes: extracting file edits from history."""

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
    timestamp: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {"type": type_, "timestamp": timestamp}
    if uuid is not None:
        row["uuid"] = uuid
    if parent is not None:
        row["parentUuid"] = parent
    if role is not None or content is not None:
        row["message"] = {"role": role or type_, "content": content}
    if extra:
        row.update(extra)
    return row


@pytest.fixture
def history_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    d = tmp_path / "projects"
    d.mkdir()
    monkeypatch.setattr(history_module, "CLAUDE_HISTORY_DIR", d)
    return d


def _write_session(
    history_dir: Path, project_path: str, sid: str, rows: list[dict]
) -> None:
    encoded = project_path.replace("/", "-")
    folder = history_dir / encoded
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{sid}.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8"
    )


def test_extracts_edit_and_write_in_order(history_dir: Path) -> None:
    rows = [
        _row("user", "u1", content="do stuff", timestamp="t1"),
        _row(
            "assistant",
            "s1",
            "u1",
            content=[
                {
                    "type": "tool_use",
                    "id": "w1",
                    "name": "Write",
                    "input": {"file_path": "a.py", "content": "print(1)\n"},
                },
                {
                    "type": "tool_use",
                    "id": "e1",
                    "name": "Edit",
                    "input": {
                        "file_path": "a.py",
                        "old_string": "print(1)",
                        "new_string": "print(2)",
                        "replace_all": False,
                    },
                },
            ],
        ),
    ]
    _write_session(history_dir, "/proj/p1", "sid", rows)

    changes = HistoryService(Path("/proj/p1"), "sid").list_changes()
    assert [c.kind for c in changes] == ["create", "edit"]
    assert [c.order for c in changes] == [0, 1]
    assert changes[0].file_path == "a.py"
    assert changes[0].new_text == "print(1)\n"
    assert changes[1].old_text == "print(1)"
    assert changes[1].new_text == "print(2)"
    # The edit produces a unified-diff body with -/+ lines.
    assert "-print(1)" in changes[1].diff
    assert "+print(2)" in changes[1].diff


def test_non_mutating_tools_ignored(history_dir: Path) -> None:
    rows = [
        _row("user", "u1", content="x", timestamp="t1"),
        _row(
            "assistant",
            "s1",
            "u1",
            content=[
                {
                    "type": "tool_use",
                    "id": "r1",
                    "name": "Read",
                    "input": {"file_path": "a.py"},
                },
                {
                    "type": "tool_use",
                    "id": "b1",
                    "name": "Bash",
                    "input": {"command": "ls"},
                },
            ],
        ),
    ]
    _write_session(history_dir, "/proj/p1", "sid", rows)
    assert HistoryService(Path("/proj/p1"), "sid").list_changes() == []


def test_missing_file_returns_empty(history_dir: Path) -> None:
    assert HistoryService(Path("/proj/none"), "nope").list_changes() == []


def test_keep_multiple_edits_to_same_file(history_dir: Path) -> None:
    """Two edits to one file must both survive, in order."""
    rows = [
        _row("user", "u1", content="x", timestamp="t1"),
        _row(
            "assistant",
            "s1",
            "u1",
            content=[
                {
                    "type": "tool_use",
                    "id": "e1",
                    "name": "Edit",
                    "input": {
                        "file_path": "a.py",
                        "old_string": "x",
                        "new_string": "y",
                        "replace_all": False,
                    },
                },
                {
                    "type": "tool_use",
                    "id": "e2",
                    "name": "Edit",
                    "input": {
                        "file_path": "a.py",
                        "old_string": "y",
                        "new_string": "z",
                        "replace_all": False,
                    },
                },
            ],
        ),
    ]
    _write_session(history_dir, "/proj/p1", "sid", rows)

    changes = HistoryService(Path("/proj/p1"), "sid").list_changes()
    assert len(changes) == 2
    assert changes[0].old_text == "x"
    assert changes[1].old_text == "y"


def test_to_dict_shape(history_dir: Path) -> None:
    rows = [
        _row("user", "u1", content="x", timestamp="t1"),
        _row(
            "assistant",
            "s1",
            "u1",
            content=[
                {
                    "type": "tool_use",
                    "id": "w1",
                    "name": "Write",
                    "input": {"file_path": "new.py", "content": "hi"},
                }
            ],
        ),
    ]
    _write_session(history_dir, "/proj/p1", "sid", rows)

    [entry] = HistoryService(Path("/proj/p1"), "sid").list_changes()
    d = entry.to_dict()
    assert set(d.keys()) == {
        "file_path",
        "kind",
        "diff",
        "old_text",
        "new_text",
        "turn_uuid",
        "order",
    }
    assert d["turn_uuid"] == "u1"
