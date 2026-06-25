"""API routes for filesystem browsing and editing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.filesystem_service import FilesystemService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/api/fs", tags=["filesystem"])


async def _get_project_service(db: AsyncSession = Depends(get_db)) -> ProjectService:
    return ProjectService(db)


def _service_for_project(project_path: str) -> FilesystemService:
    return FilesystemService(Path(project_path))


@router.get("/home")
async def get_home() -> dict[str, str]:
    """Return the user's home directory."""
    return {"path": str(Path.home().resolve())}


@router.get("/browse-absolute")
async def browse_absolute(path: str = "") -> dict[str, Any]:
    """Browse any absolute directory path for the path picker dialog."""
    target = Path(path).expanduser().resolve() if path else Path.home().resolve()
    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {path}")

    entries = []
    for item in sorted(
        target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())
    ):
        entries.append(
            {
                "name": item.name,
                "path": str(item.resolve()),
                "type": "directory" if item.is_dir() else "file",
            }
        )
    return {"current_path": str(target), "entries": entries}


@router.get("/browse")
async def browse(
    project_id: str,
    path: str = "",
    project_service: ProjectService = Depends(_get_project_service),
) -> dict[str, Any]:
    """List directory entries."""
    project = await project_service.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    service = _service_for_project(project.path)
    try:
        return service.browse(path)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except NotADirectoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/read")
async def read(
    project_id: str,
    path: str = Query(...),
    project_service: ProjectService = Depends(_get_project_service),
) -> dict[str, str]:
    """Read a file."""
    project = await project_service.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    service = _service_for_project(project.path)
    try:
        return {"content": service.read(path)}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except IsADirectoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/write")
async def write(
    payload: dict[str, Any],
    project_service: ProjectService = Depends(_get_project_service),
) -> dict[str, str]:
    """Write a file."""
    project_id = payload.get("project_id")
    path = payload.get("path")
    content = payload.get("content")
    if not project_id or not path or content is None:
        raise HTTPException(
            status_code=422, detail="project_id, path and content are required"
        )

    project = await project_service.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    service = _service_for_project(project.path)
    try:
        service.write(path, content)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {"status": "ok"}
