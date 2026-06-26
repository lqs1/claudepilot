"""API routes for sending messages and controlling sessions.

Message read/now comes from the Claude Code CLI jsonl history (the single
source of truth), not from the SQLite messages table. Deletes rewrite the
jsonl in place (paired with their replies) so the CLI can still resume.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.setting_service import _DEFAULT_SETTINGS
from app.database import async_session_maker, get_db
from app.services.claude_manager import session_manager
from app.services.history_service import HistoryService
from app.services.project_service import ProjectService
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions/{session_id}", tags=["messages"])


async def _get_project_service(db: AsyncSession = Depends(get_db)) -> ProjectService:
    return ProjectService(db)


async def _get_session_service(db: AsyncSession = Depends(get_db)) -> SessionService:
    return SessionService(db)


async def _resolve_session(
    session_id: str,
    session_service: SessionService,
    project_service: ProjectService,
) -> tuple[Any, Any]:
    """Load a session and its project, or 404."""
    session = await session_service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    project = await project_service.get_project(session.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return session, project


async def _ensure_session_running(
    session_id: str,
    project_path: Path,
    language: str,
    settings: dict[str, Any] | None = None,
    initial_message: str | None = None,
) -> None:
    """Start a Claude session if it is not already running."""
    logger.info(
        "Ensuring session %s is running (status=%s)",
        session_id,
        session_manager.get_status(session_id),
    )
    if session_manager.get_status(session_id) == "running":
        if initial_message:
            logger.info("Session %s already running, sending message", session_id)
            await session_manager.send_message(session_id, initial_message)
        return

    # Only resume when the CLI actually has an on-disk conversation to recover.
    # The CLI writes one jsonl per session; if it exists with content, the
    # session can be resumed, otherwise resuming would crash with
    # "No conversation found with session ID".
    resume = HistoryService(project_path, session_id).exists()

    logger.info("Starting Claude session %s for project %s", session_id, project_path)
    merged = {**_DEFAULT_SETTINGS, **(settings or {})}
    model = merged.get("model") or None
    permission_mode = merged.get("permission_mode", "acceptEdits")
    effort = merged.get("effort") or None
    max_turns = merged.get("max_turns")
    tools_enabled = bool(merged.get("tools_enabled", True))

    try:
        await session_manager.start_session(
            session_id=session_id,
            project_path=project_path,
            language=language,
            model=model,
            permission_mode=permission_mode,
            effort=effort,
            max_turns=max_turns,
            tools_enabled=tools_enabled,
            mcp_servers=merged.get("mcp_servers"),
            initial_message=initial_message,
            resume=resume,
        )
        logger.info(
            "Session %s started, engine status=%s",
            session_id,
            session_manager.get_status(session_id),
        )
    except Exception:
        logger.exception("Failed to start Claude session %s", session_id)
        raise

    # Record start time in DB after successful launch
    async with async_session_maker() as db:
        svc = SessionService(db)
        await svc.update_started_at(session_id, datetime.now(timezone.utc))


@router.post("/start")
async def start_session(
    session_id: str,
    project_service: ProjectService = Depends(_get_project_service),
    session_service: SessionService = Depends(_get_session_service),
) -> dict[str, Any]:
    """Start the Claude CLI for a session."""
    session, project = await _resolve_session(
        session_id, session_service, project_service
    )

    await _ensure_session_running(
        session_id, Path(project.path), session.language, settings=session.settings
    )
    await session_service.update_status(session_id, "running")
    return {"status": "running"}


@router.post("/stop")
async def stop_session(
    session_id: str,
    session_service: SessionService = Depends(_get_session_service),
) -> dict[str, Any]:
    """Stop the Claude CLI for a session."""
    session = await session_service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    await session_manager.stop_session(session_id)
    await session_service.update_status(session_id, "stopped")
    await session_service.update_started_at(session_id, None)
    return {"status": "stopped"}


@router.post("/resume")
async def resume_session(
    session_id: str,
    project_service: ProjectService = Depends(_get_project_service),
    session_service: SessionService = Depends(_get_session_service),
) -> dict[str, Any]:
    """Resume a previously stopped Claude CLI session."""
    session, project = await _resolve_session(
        session_id, session_service, project_service
    )

    if session_manager.get_status(session_id) == "running":
        return {"status": "running"}

    # Only --resume when the CLI has on-disk history; otherwise start fresh.
    resume = HistoryService(Path(project.path), session_id).exists()

    await session_manager.start_session(
        session_id=session_id,
        project_path=Path(project.path),
        language=session.language,
        resume=resume,
    )
    await session_service.update_status(session_id, "running")
    return {"status": "running"}


@router.post("/messages")
async def send_message(
    session_id: str,
    payload: dict[str, Any],
    project_service: ProjectService = Depends(_get_project_service),
    session_service: SessionService = Depends(_get_session_service),
) -> dict[str, Any]:
    """Send a user message to a session, auto-starting it if needed.

    The message itself is not persisted by us: the CLI writes it to its own
    jsonl the moment it processes the stdin input, and that file is the read
    path for history.
    """
    content = payload.get("content")
    if not content:
        raise HTTPException(status_code=422, detail="content is required")

    session, project = await _resolve_session(
        session_id, session_service, project_service
    )

    await _ensure_session_running(
        session_id,
        Path(project.path),
        session.language,
        settings=session.settings,
        initial_message=content,
    )
    return {"status": "sent"}


@router.get("/messages")
async def list_messages(
    session_id: str,
    project_service: ProjectService = Depends(_get_project_service),
    session_service: SessionService = Depends(_get_session_service),
) -> dict[str, Any]:
    """List messages for a session, read from the CLI's jsonl history."""
    session, project = await _resolve_session(
        session_id, session_service, project_service
    )
    messages = HistoryService(Path(project.path), session_id).list_messages()
    return {"messages": messages}


@router.get("/changes")
async def list_changes(
    session_id: str,
    project_service: ProjectService = Depends(_get_project_service),
    session_service: SessionService = Depends(_get_session_service),
) -> dict[str, Any]:
    """List file-changing tool calls (Edit/Write) for a session, in order."""
    session, project = await _resolve_session(
        session_id, session_service, project_service
    )
    changes = HistoryService(Path(project.path), session_id).list_changes()
    return {"changes": [c.to_dict() for c in changes]}


@router.delete("/turns/{turn_uuid}")
async def delete_turn(
    session_id: str,
    turn_uuid: str,
    project_service: ProjectService = Depends(_get_project_service),
    session_service: SessionService = Depends(_get_session_service),
) -> dict[str, Any]:
    """Delete a whole turn (prompt + its reply) from the CLI's jsonl history.

    Refuses while the CLI is running to avoid racing the process that owns the
    file.
    """
    if session_manager.get_status(session_id) == "running":
        raise HTTPException(
            status_code=409,
            detail="Stop the session before deleting history",
        )

    session, project = await _resolve_session(
        session_id, session_service, project_service
    )
    history = HistoryService(Path(project.path), session_id)
    if not history.exists():
        raise HTTPException(status_code=404, detail="No history for this session")

    deleted = history.delete_turn(turn_uuid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Turn not found")
    return {"deleted": True, "turn_uuid": turn_uuid}


@router.post("/answer")
async def answer_question(
    session_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Answer an AskUserQuestion tool call."""
    tool_use_id = payload.get("tool_use_id")
    answers = payload.get("answers")
    if not tool_use_id or not answers:
        raise HTTPException(
            status_code=422, detail="tool_use_id and answers are required"
        )

    try:
        await session_manager.answer_question(session_id, tool_use_id, answers)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": "answered"}


@router.post("/permission")
async def respond_permission(
    session_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Respond to a permission request."""
    tool_use_id = payload.get("tool_use_id")
    allowed = payload.get("allowed", False)
    if not tool_use_id:
        raise HTTPException(status_code=422, detail="tool_use_id is required")

    try:
        await session_manager.respond_permission(session_id, tool_use_id, allowed)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": "responded"}


@router.post("/plan-feedback")
async def plan_feedback(
    session_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Send plan feedback (approve, reject, or custom feedback) to a session."""
    action = payload.get("action")
    message = payload.get("message", "")
    if action not in ("approve", "reject", "feedback"):
        raise HTTPException(
            status_code=422, detail="action must be 'approve', 'reject', or 'feedback'"
        )

    try:
        await session_manager.send_plan_feedback(session_id, action, message)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": "sent"}
