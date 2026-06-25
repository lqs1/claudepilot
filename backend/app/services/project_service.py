"""Business logic for project management."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project


class ProjectService:
    """Service for project CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_projects(self) -> list[Project]:
        """Return all projects ordered by updated time descending."""
        result = await self.session.execute(
            select(Project).order_by(Project.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_project(self, project_id: str) -> Project | None:
        """Fetch a project by ID."""
        return await self.session.get(Project, project_id)

    async def get_project_by_path(self, path: str) -> Project | None:
        """Fetch a project by its absolute path."""
        resolved = str(Path(path).resolve())
        result = await self.session.execute(
            select(Project).where(Project.path == resolved)
        )
        return result.scalar_one_or_none()

    async def create_project(self, name: str, path: str) -> Project:
        """Create a new project or return existing one with the same path."""
        project_path = Path(path).resolve()
        project_path.mkdir(parents=True, exist_ok=True)
        existing = await self.get_project_by_path(str(project_path))
        if existing is not None:
            return existing
        project = Project(name=name, path=str(project_path))
        self.session.add(project)
        await self.session.commit()
        await self.session.refresh(project)
        return project

    async def delete_project(self, project_id: str) -> bool:
        """Delete a project by ID."""
        project = await self.get_project(project_id)
        if project is None:
            return False
        await self.session.delete(project)
        await self.session.commit()
        return True

    async def to_dict(self, project: Project) -> dict[str, Any]:
        """Serialize a project to a dictionary."""
        return {
            "id": project.id,
            "name": project.name,
            "path": project.path,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
        }
