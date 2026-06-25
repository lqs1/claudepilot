"""API routes for session management."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.project_service import ProjectService
from app.services.session_service import SessionService

router = APIRouter(prefix="/api/projects/{project_id}/sessions", tags=["sessions"])


async def _get_session_service(db: AsyncSession = Depends(get_db)) -> SessionService:
    return SessionService(db)


async def _get_project_service(db: AsyncSession = Depends(get_db)) -> ProjectService:
    return ProjectService(db)


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
