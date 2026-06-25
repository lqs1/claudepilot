"""Filesystem operations scoped to a project root."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class FilesystemService:
    """Provide safe filesystem access within a project directory."""

    def __init__(self, project_path: Path) -> None:
        self.project_path = Path(project_path).resolve()

    def _resolve(self, relative_path: str) -> Path:
        """Resolve a project-relative path and enforce boundary."""
        target = (self.project_path / relative_path).resolve()
        try:
            target.relative_to(self.project_path)
        except ValueError as exc:
            raise PermissionError(
                f"Path escapes project root: {relative_path}"
            ) from exc
        return target

    def browse(self, relative_path: str = "") -> dict[str, Any]:
        """List directory entries relative to the project root."""
        target = self._resolve(relative_path)
        if not target.exists():
            raise FileNotFoundError(f"Path not found: {relative_path}")
        if not target.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {relative_path}")

        entries = []
        for item in sorted(
            target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())
        ):
            entries.append(
                {
                    "name": item.name,
                    "path": str(item.relative_to(self.project_path)),
                    "type": "directory" if item.is_dir() else "file",
                }
            )
        return {"entries": entries}

    def read(self, relative_path: str) -> str:
        """Read a text file relative to the project root."""
        target = self._resolve(relative_path)
        if not target.exists():
            raise FileNotFoundError(f"File not found: {relative_path}")
        if target.is_dir():
            raise IsADirectoryError(f"Path is a directory: {relative_path}")
        return target.read_text(encoding="utf-8")

    def write(self, relative_path: str, content: str) -> None:
        """Write a text file relative to the project root."""
        target = self._resolve(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
