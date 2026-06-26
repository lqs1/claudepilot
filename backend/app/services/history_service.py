"""Read and edit Claude Code CLI session history (per-session jsonl).

The CLI keeps each session as an append-only JSONL file under
``~/.claude/projects/<encoded-project-path>/<session-id>.jsonl``. Each line is
an event; real messages are lines with ``type`` of ``user`` or ``assistant``
that carry a ``uuid``/``parentUuid`` chain. Metadata rows
(``queue-operation``, ``attachment``, ``last-prompt``, ``ai-title`` ...) are
ignored for display but must be preserved (or correctly filtered) when the
file is rewritten for deletion, so the CLI can still ``--resume`` it.

This module is the single source of truth for that file format.
"""

from __future__ import annotations

import difflib
import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import CLAUDE_HISTORY_DIR

logger = logging.getLogger(__name__)


def encode_project_path(project_path: Path) -> str:
    """Encode a project path the same way the CLI names its history folder.

    The CLI replaces path separators (``/``) **and dots** (``.``) with ``-``.
    The leading ``/`` therefore becomes a leading ``-``. The absolute path is
    resolved first (on macOS this turns ``/var`` into ``/private/var``), which
    matches what the CLI itself uses as the cwd-derived folder name.
    """
    resolved = str(Path(project_path).resolve())
    return resolved.replace("/", "-").replace(".", "-")


@dataclass
class Turn:
    """A user-visible conversation turn: a prompt plus its full assistant reply.

    A turn groups everything between one user prompt and the next top-level
    prompt: the user message, its attachments, the assistant's (possibly
    multi-line) reply, and any tool_use / tool_result pairs.

    ``uuid`` is the originating user message's uuid and is the stable handle
    used to delete the whole turn.
    """

    uuid: str
    role: str = "user"
    type: str = "text"
    user_text: str = ""
    assistant_text: str = ""
    tool_uses: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = ""

    def to_messages(self) -> list[dict[str, Any]]:
        """Flatten the turn into Message-shaped dicts the API/UI expects.

        The user prompt becomes one ''text/user'' message; the assistant reply
        becomes one ''text/assistant'' message (omitted when empty and there
        are no tool calls). Every message carries the turn ''uuid'' so the UI
        can delete the whole turn in one go.
        """
        msgs: list[dict[str, Any]] = [
            {
                "id": self.uuid,
                "uuid": self.uuid,
                "session_id": "",
                "role": "user",
                "type": "text",
                "content": self.user_text,
                "created_at": self.created_at,
            }
        ]
        if self.assistant_text or self.tool_uses:
            msgs.append(
                {
                    "id": f"{self.uuid}-reply",
                    "uuid": self.uuid,
                    "session_id": "",
                    "role": "assistant",
                    "type": "text",
                    "content": self.assistant_text,
                    "tool_uses": self.tool_uses,
                    "created_at": self.created_at,
                }
            )
        return msgs


@dataclass
class ChangeEntry:
    """A single file-changing tool call extracted from the history.

    Ordered by when it happened in the conversation. The UI groups these by
    ``file_path`` while keeping each edit's own before/after (a file can be
    edited several times, each with its own diff).
    """

    file_path: str
    """``"edit"`` (Edit tool) or ``"create"`` (Write tool)."""
    kind: str
    """Unified-diff text (from difflib) for display. Empty for creates with
    no prior content to diff against."""
    diff: str
    """The 'before' text, where available (Edit only)."""
    old_text: str
    """The 'after' text."""
    new_text: str
    """Originating turn uuid, so changes can be linked back to the prompt."""
    turn_uuid: str
    """0-based order within the whole session."""
    order: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "kind": self.kind,
            "diff": self.diff,
            "old_text": self.old_text,
            "new_text": self.new_text,
            "turn_uuid": self.turn_uuid,
            "order": self.order,
        }


class HistoryService:
    """Read and rewind a single session's jsonl history."""

    def __init__(self, project_path: Path, session_id: str) -> None:
        self.project_path = Path(project_path)
        self.session_id = session_id

    def jsonl_path(self) -> Path:
        """Return the jsonl path for this session (may not exist yet)."""
        return (
            CLAUDE_HISTORY_DIR
            / encode_project_path(self.project_path)
            / (f"{self.session_id}.jsonl")
        )

    def exists(self) -> bool:
        """Return True if the on-disk session jsonl exists and is non-empty."""
        path = self.jsonl_path()
        return path.exists() and path.stat().st_size > 0

    def list_turns(self) -> list[Turn]:
        """Read the history and return the ordered list of user-visible turns."""
        path = self.jsonl_path()
        if not path.exists():
            return []

        rows = _read_rows(path)
        if not rows:
            return []

        # Maps message uuid -> row, to walk the parent chain.
        by_uuid: dict[str, dict[str, Any]] = {
            r["uuid"]: r for r in rows if r.get("uuid")
        }
        turn_starts = _top_level_user_prompts(rows, by_uuid)

        turns: list[Turn] = []
        for index, start in enumerate(turn_starts):
            end = turn_starts[index + 1] if index + 1 < len(turn_starts) else len(rows)
            turns.append(_aggregate_turn(rows[start:end], by_uuid))
        return turns

    def list_messages(self) -> list[dict[str, Any]]:
        """Return a flat list of Message dicts for the whole session.

        This is the display/read path. It is independent of SQLAlchemy: the
        SQLite ``messages`` table is no longer the source of truth.
        """
        msgs: list[dict[str, Any]] = []
        for turn in self.list_turns():
            msgs.extend(turn.to_messages())
        return msgs

    def list_changes(self) -> list[ChangeEntry]:
        """Return the file-changing tool calls (Edit/Write) in order.

        Extracted from each turn's tool_uses. Read/Bash/etc. are ignored. The
        result is a time-ordered list (the UI groups by file); each entry
        carries its own before/after diff so multiple edits to one file all
        stay visible.
        """
        changes: list[ChangeEntry] = []
        order = 0
        for turn in self.list_turns():
            for tool in turn.tool_uses:
                name = tool.get("name", "")
                inp = tool.get("input") or {}
                entry = _tool_to_change(name, inp, turn.uuid, order)
                if entry is not None:
                    changes.append(entry)
                    order += 1
        return changes

    def delete_turn(self, turn_uuid: str) -> bool:
        """Remove the turn whose prompt has ``turn_uuid`` from the jsonl.

        All rows belonging to that turn (user prompt, attachments, the
        assistant reply, tool calls and results) are dropped, and the
        parentUuid chain is repaired so the file stays resumable. Returns
        True if anything was written, False if the turn was not found.
        """
        path = self.jsonl_path()
        if not path.exists():
            return False

        rows = _read_rows(path)
        by_uuid = {r["uuid"]: r for r in rows if r.get("uuid")}
        turn_starts = _top_level_user_prompts(rows, by_uuid)

        target_index = None
        for i, start in enumerate(turn_starts):
            r = rows[start]
            if r.get("uuid") == turn_uuid:
                target_index = i
                break
        if target_index is None:
            return False

        # Rows belonging to the deleted turn.
        deletable: set[str | None] = set()
        seg_start = turn_starts[target_index]
        seg_end = (
            turn_starts[target_index + 1]
            if target_index + 1 < len(turn_starts)
            else len(rows)
        )
        for r in rows[seg_start:seg_end]:
            if r.get("uuid"):
                deletable.add(r["uuid"])

        # The last kept row before the deleted segment (for chain repair), or
        # None if we deleted right from the start.
        last_kept_before: str | None = None
        for r in reversed(rows[:seg_start]):
            if r.get("uuid"):
                last_kept_before = r["uuid"]
                break

        kept: list[dict[str, Any]] = []
        for r in rows:
            u = r.get("uuid")
            if u in deletable:
                continue
            kept.append(r)

        # Repair the chain: the first top-level user prompt that survives the
        # deletion (if any) must reparent onto the last kept row before the
        # deleted segment so the CLI can still walk the full history.
        surviving_starts = _top_level_user_prompts(
            kept, {r["uuid"]: r for r in kept if r.get("uuid")}
        )
        kept_with_chain = [_clone_row(r) for r in kept]
        for s in surviving_starts:
            r = kept_with_chain[s]
            if r.get("uuid") == turn_uuid:
                continue
            # Only reparent a row whose parent was just deleted.
            if r.get("parentUuid") in deletable:
                r["parentUuid"] = last_kept_before

        _atomic_write_jsonl(path, kept_with_chain)
        logger.info(
            "Deleted turn %s from %s (removed %d rows)",
            turn_uuid,
            path,
            seg_end - seg_start,
        )
        return True


# --- Row helpers ---------------------------------------------------------


def _read_rows(path: Path) -> list[dict[str, Any]]:
    """Read and parse all JSON objects from a jsonl file."""
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("Skipping unparseable line in %s", path)
    return rows


def _tool_to_change(
    name: str, input_: dict[str, Any], turn_uuid: str, order: int
) -> ChangeEntry | None:
    """Convert an Edit/Write tool_use input into a ChangeEntry, else None."""
    file_path = str(input_.get("file_path") or "")
    if not file_path:
        return None

    if name == "Write":
        new_text = str(input_.get("content") or "")
        return ChangeEntry(
            file_path=file_path,
            kind="create",
            diff="",  # no prior content to diff against
            old_text="",
            new_text=new_text,
            turn_uuid=turn_uuid,
            order=order,
        )

    if name in ("Edit", "MultiEdit", "NotebookEdit"):
        old_text = str(input_.get("old_string") or "")
        new_text = str(input_.get("new_string") or "")
        diff = _make_unified_diff(file_path, old_text, new_text)
        return ChangeEntry(
            file_path=file_path,
            kind="edit",
            diff=diff,
            old_text=old_text,
            new_text=new_text,
            turn_uuid=turn_uuid,
            order=order,
        )

    return None


def _make_unified_diff(file_path: str, old_text: str, new_text: str) -> str:
    """Build a minimal unified diff string for display."""
    # Use the basename for the file labels so absolute paths don't mangle the
    # header (which would otherwise read "a//private/...").
    name = Path(file_path).name or file_path
    diff = difflib.unified_diff(
        old_text.splitlines(),
        new_text.splitlines(),
        fromfile=f"a/{name}",
        tofile=f"b/{name}",
        lineterm="",
    )
    return "\n".join(diff)


def _clone_row(row: dict[str, Any]) -> dict[str, Any]:
    """Shallow copy so we can mutate parentUuid without touching the source."""
    clone = dict(row)
    return clone


def _is_message_row(row: dict[str, Any]) -> bool:
    """A real user/assistant message row owns a uuid and a message payload."""
    return bool(row.get("uuid")) and isinstance(row.get("message"), dict)


def _top_level_user_prompts(
    rows: list[dict[str, Any]], by_uuid: dict[str, dict[str, Any]]
) -> list[int]:
    """Return indices of rows that start a new turn.

    A turn starts at a ``user`` message whose ``text`` content is a real prompt
    (not a tool_result and not a sidechain/attachment). Tool-result user rows
    carry list content and are never turn starts.
    """
    starts: list[int] = []
    for i, row in enumerate(rows):
        if not _is_message_row(row) or row.get("type") != "user":
            continue
        message = row["message"]
        content = message.get("content")
        # A prompt is string content; tool results are list content.
        if not isinstance(content, str):
            continue
        # Skip sidechain/attachment-only entries the CLI marks as not mainline.
        if row.get("isSidechain"):
            continue
        starts.append(i)
    return starts


def _aggregate_turn(
    segment: list[dict[str, Any]], _by_uuid: dict[str, dict[str, Any]]
) -> Turn:
    """Collapse a turn's rows into one readable Turn."""
    turn = Turn(uuid="")
    for row in segment:
        if not _is_message_row(row):
            # attachment / metadata: capture the timestamp if we have none yet.
            if not turn.created_at and row.get("timestamp"):
                turn.created_at = str(row.get("timestamp"))
            continue
        message = row["message"]
        content = message.get("content")
        role = row.get("type") or message.get("role")
        if role == "user":
            if isinstance(content, str):
                if not turn.uuid:
                    turn.uuid = str(row.get("uuid", ""))
                turn.user_text = content
                turn.created_at = str(row.get("timestamp", turn.created_at))
        elif role == "assistant":
            _accumulate_assistant(turn, row, content)
    return turn


def _accumulate_assistant(turn: Turn, row: dict[str, Any], content: Any) -> None:
    """Merge an assistant message's content blocks into the turn's reply."""
    if not isinstance(content, list):
        if isinstance(content, str) and content:
            turn.assistant_text += content
        return
    for block in content:
        if not isinstance(block, dict):
            continue
        kind = block.get("type")
        if kind == "text" and block.get("text"):
            turn.assistant_text += block["text"]
        elif kind == "tool_use":
            turn.tool_uses.append(
                {
                    "id": block.get("id", ""),
                    "name": block.get("name", ""),
                    "input": block.get("input", {}),
                }
            )


def _atomic_write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write rows back atomically: temp file in the same dir, then rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    directory = str(path.parent)
    fd, tmp_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=directory
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False))
                handle.write("\n")
        os.replace(tmp_name, path)
    except Exception:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
        raise


__all__ = ["HistoryService", "Turn", "ChangeEntry", "encode_project_path"]
