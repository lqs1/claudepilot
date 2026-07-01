"""API routes for session management."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.messages import _ensure_session_running
from app.database import get_db
from app.services.preset_service import PresetService
from app.services.project_service import ProjectService
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects/{project_id}/sessions", tags=["sessions"])


async def _get_session_service(db: AsyncSession = Depends(get_db)) -> SessionService:
    return SessionService(db)


async def _get_project_service(db: AsyncSession = Depends(get_db)) -> ProjectService:
    return ProjectService(db)


async def _get_preset_service(db: AsyncSession = Depends(get_db)) -> PresetService:
    return PresetService(db)


@router.get("")
async def list_sessions(
    project_id: str,
    project_service: ProjectService = Depends(_get_project_service),
    session_service: SessionService = Depends(_get_session_service),
) -> dict[str, Any]:
    """List sessions for a project."""
    project = await project_service.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    sessions = await session_service.list_sessions(project_id)
    return {"sessions": [session_service.to_dict(s) for s in sessions]}


@router.post("")
async def create_session(
    project_id: str,
    payload: dict[str, Any],
    project_service: ProjectService = Depends(_get_project_service),
    session_service: SessionService = Depends(_get_session_service),
) -> dict[str, Any]:
    """Create a new session."""
    project = await project_service.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    title = payload.get("title", "New Session")
    language = payload.get("language", "zh")
    settings = payload.get("settings")
    if not isinstance(title, str) or not title.strip():
        raise HTTPException(status_code=422, detail="Session title is required")

    session = await session_service.create_session(
        project_id=project_id,
        title=title.strip(),
        language=language,
        settings=settings,
    )
    return {"session": session_service.to_dict(session)}


@router.post("/broadcast")
async def broadcast_sessions(
    project_id: str,
    payload: dict[str, Any],
    project_service: ProjectService = Depends(_get_project_service),
    session_service: SessionService = Depends(_get_session_service),
    preset_service: PresetService = Depends(_get_preset_service),
) -> dict[str, Any]:
    """Create one session per configuration and send the same prompt to each.

    This is the parallel/broadcast entrypoint: pick presets, and each becomes
    a fresh session (with that preset's settings) all running the same prompt
    concurrently. Returns the created sessions so the UI can list them.

    Body: {prompt: str, language?: str, configurations: [{preset_id?, title?}]}.
    """
    project = await project_service.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise HTTPException(status_code=422, detail="prompt is required")

    configurations = payload.get("configurations")
    if not isinstance(configurations, list) or not configurations:
        raise HTTPException(
            status_code=422,
            detail="configurations must be a non-empty list",
        )

    language = payload.get("language", "zh")
    project_path = Path(project.path)

    # Resolve each configuration into (title, settings) up front so bad
    # preset ids fail fast (before creating any session).
    plan: list[tuple[str, dict[str, Any]]] = []
    short = prompt.strip()[:20]
    for idx, cfg in enumerate(configurations):
        if not isinstance(cfg, dict):
            raise HTTPException(
                status_code=422, detail="each configuration must be an object"
            )
        settings: dict[str, Any] = {}
        title = cfg.get("title")
        if cfg.get("preset_id"):
            preset = await preset_service.get_preset(cfg["preset_id"])
            if preset is None:
                raise HTTPException(
                    status_code=404, detail=f"Preset not found: {cfg['preset_id']}"
                )
            settings = dict(preset.settings)
            if not title:
                title = preset.name
        if not title:
            title = f"{short}…" if configurations else short
        plan.append((str(title), settings))

    async def _spawn(idx: int) -> dict[str, Any]:
        title, settings = plan[idx]
        # Append the shared prompt snippet to the title so multiple presets
        # answering the same prompt are easy to tell apart in the sidebar.
        label = title if len(plan) == 1 else f"{title} · {short}"
        # Each spawned task uses its own DB session: asyncio.gather runs them
        # concurrently and a shared SQLAlchemy session is not safe to mutate
        # from multiple coroutines at once.
        from app.database import async_session_maker

        async with async_session_maker() as db:
            svc = SessionService(db)
            session = await svc.create_session(
                project_id=project_id,
                title=label,
                language=language,
                settings=settings or None,
            )
            result = svc.to_dict(session)
        # Start the CLI outside the DB transaction and send the prompt as the
        # first message, concurrently with the other spawned sessions.
        await _ensure_session_running(
            session_id=session.id,
            project_path=project_path,
            language=language,
            settings=session.settings,
            initial_message=prompt.strip(),
        )
        return result

    created = await asyncio.gather(*(_spawn(i) for i in range(len(plan))))
    return {"sessions": list(created)}


@router.get("/{session_id}")
async def get_session(
    project_id: str,
    session_id: str,
    project_service: ProjectService = Depends(_get_project_service),
    session_service: SessionService = Depends(_get_session_service),
) -> dict[str, Any]:
    """Get a single session."""
    project = await project_service.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    session = await session_service.get_session(session_id)
    if session is None or session.project_id != project_id:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session": session_service.to_dict(session)}
