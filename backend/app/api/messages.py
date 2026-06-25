"""API routes for sending messages and controlling sessions."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.settings import _default_settings
from app.database import async_session_maker, get_db
from app.services.claude_manager import session_manager
from app.services.project_service import ProjectService
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions/{session_id}", tags=["messages"])


async def _get_project_service(db: AsyncSession = Depends(get_db)) -> ProjectService:
    return ProjectService(db)


async def _get_session_service(db: AsyncSession = Depends(get_db)) -> SessionService:
    return SessionService(db)


def _make_persist_callback(session_id: str) -> Any:
    """Return a callback that persists Claude events for a session."""

    def callback(sid: str, payload: dict[str, Any]) -> None:
        if sid != session_id:
            return
        event_type = payload.get("type")
        if event_type == "assistant":
            text = payload.get("text", "")
            if text:
                _persist_message(session_id, "assistant", "text", text)
            for tool in payload.get("tool_uses", []):
                _persist_message(
                    session_id,
                    "tool",
                    "tool_use",
                    f"Using tool: {tool.get('name')}",
                    tool_name=tool.get("name"),
                    tool_input=tool.get("input"),
                )

    return callback


def _persist_message(
    session_id: str,
    role: str,
    type: str,
    content: str,
    *,
    tool_name: str | None = None,
    tool_input: dict[str, Any] | None = None,
) -> None:
    """Persist a message asynchronously using a fresh DB session."""
    import asyncio

    asyncio.create_task(
        _save_message(
            session_id,
            role,
            type,
            content,
            tool_name=tool_name,
            tool_input=tool_input,
        )
    )


async def _save_message(
    session_id: str,
    role: str,
    type: str,
    content: str,
    *,
    tool_name: str | None = None,
    tool_input: dict[str, Any] | None = None,
) -> None:
    """Save a message using a fresh database session."""
    async with async_session_maker() as db:
        service = SessionService(db)
        try:
            await service.add_message(
                session_id=session_id,
                role=role,
                type=type,
                content=content,
                tool_name=tool_name,
                tool_input=tool_input,
            )
        except Exception:
            import logging

            logging.getLogger(__name__).exception("Failed to persist message")


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

    logger.info("Starting Claude session %s for project %s", session_id, project_path)
    session_manager.register_persist_callback(
        session_id, _make_persist_callback(session_id)
    )

    merged = {**_default_settings, **(settings or {})}
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
            initial_message=initial_message,
        )
        logger.info(
            "Session %s started, engine status=%s",
            session_id,
            session_manager.get_status(session_id),
        )
    except Exception:
        logger.exception("Failed to start Claude session %s", session_id)
        raise


@router.post("/start")
async def start_session(
    session_id: str,
    project_service: ProjectService = Depends(_get_project_service),
    session_service: SessionService = Depends(_get_session_service),
) -> dict[str, Any]:
    """Start the Claude CLI for a session."""
    session = await session_service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    project = await project_service.get_project(session.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

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
    return {"status": "stopped"}


@router.post("/resume")
async def resume_session(
    session_id: str,
    project_service: ProjectService = Depends(_get_project_service),
    session_service: SessionService = Depends(_get_session_service),
) -> dict[str, Any]:
    """Resume a previously stopped Claude CLI session."""
    session = await session_service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    project = await project_service.get_project(session.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if session_manager.get_status(session_id) == "running":
        return {"status": "running"}

    session_manager.register_persist_callback(
        session_id, _make_persist_callback(session_id)
    )
    await session_manager.start_session(
        session_id=session_id,
        project_path=Path(project.path),
        language=session.language,
        resume=True,
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
    """Send a user message to a session, auto-starting it if needed."""
    content = payload.get("content")
    if not content:
        raise HTTPException(status_code=422, detail="content is required")

    session = await session_service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    await session_service.add_message(
        session_id=session_id,
        role="user",
        type="text",
        content=content,
    )

    project = await project_service.get_project(session.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

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
    session_service: SessionService = Depends(_get_session_service),
) -> dict[str, Any]:
    """List messages for a session."""
    session = await session_service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = await session_service.list_messages(session_id)
    return {"messages": [session_service.message_to_dict(m) for m in messages]}


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
