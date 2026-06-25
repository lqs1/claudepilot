"""API routes for project management."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.project_service import ProjectService

router = APIRouter(prefix="/api/projects", tags=["projects"])


async def _get_service(session: AsyncSession = Depends(get_db)) -> ProjectService:
    return ProjectService(session)


@router.get("")
async def list_projects(
    service: ProjectService = Depends(_get_service),
) -> dict[str, Any]:
    """List all projects."""
    projects = await service.list_projects()
    return {"projects": [await service.to_dict(p) for p in projects]}


@router.post("")
async def create_project(
    payload: dict[str, str],
    service: ProjectService = Depends(_get_service),
) -> dict[str, Any]:
    """Create a new project."""
    name = payload.get("name")
    path = payload.get("path")
    if not name or not path:
        raise HTTPException(status_code=422, detail="name and path are required")
    project = await service.create_project(name, path)
    return {"project": await service.to_dict(project)}


@router.post("/open")
async def open_project(
    payload: dict[str, str],
    service: ProjectService = Depends(_get_service),
) -> dict[str, Any]:
    """Open an existing local directory as a project."""
    path_str = payload.get("path")
    if not path_str:
        raise HTTPException(status_code=422, detail="path is required")

    resolved = Path(path_str).expanduser().resolve()
    if not resolved.exists():
        raise HTTPException(status_code=400, detail=f"Path does not exist: {path_str}")
    if not resolved.is_dir():
        raise HTTPException(
            status_code=400, detail=f"Path is not a directory: {path_str}"
        )

    project = await service.create_project(resolved.name, str(resolved))
    return {"project": await service.to_dict(project)}


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    service: ProjectService = Depends(_get_service),
) -> dict[str, Any]:
    """Get a single project."""
    project = await service.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": await service.to_dict(project)}


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    service: ProjectService = Depends(_get_service),
) -> dict[str, Any]:
    """Delete a project."""
    deleted = await service.delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"deleted": True}
