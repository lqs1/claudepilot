"""API routes for global and session settings."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.session_service import SessionService

router = APIRouter(prefix="/api/settings", tags=["settings"])

# Global default settings stored in memory (no persistent DB table for now).
_default_settings: dict[str, Any] = {
    "model": "claude-sonnet-4-20250514",
    "effort": "normal",
    "permission_mode": "acceptEdits",
    "tools_enabled": True,
}


def _get_session_service(db: AsyncSession = Depends(get_db)) -> SessionService:
    return SessionService(db)


@router.get("")
async def get_settings() -> dict[str, Any]:
    """Return the global default settings."""
    return {"settings": _default_settings.copy()}


@router.put("")
async def update_settings(payload: dict[str, Any]) -> dict[str, Any]:
    """Update the global default settings."""
    global _default_settings
    allowed_keys = {"model", "effort", "permission_mode", "tools_enabled", "max_turns"}
    for key, value in payload.items():
        if key not in allowed_keys:
            raise HTTPException(status_code=422, detail=f"Unknown setting: {key}")
        _default_settings[key] = value
    return {"settings": _default_settings.copy()}


@router.get("/session/{session_id}")
async def get_session_settings(
    session_id: str,
    session_service: SessionService = Depends(_get_session_service),
) -> dict[str, Any]:
    """Return session-specific settings merged with global defaults."""
    session = await session_service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    overrides = session.settings or {}
    merged = {**_default_settings, **overrides}
    return {"settings": merged}


@router.put("/session/{session_id}")
async def update_session_settings(
    session_id: str,
    payload: dict[str, Any],
    session_service: SessionService = Depends(_get_session_service),
) -> dict[str, Any]:
    """Update session-specific settings overrides."""
    session = await session_service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    allowed_keys = {"model", "effort", "permission_mode", "tools_enabled", "max_turns"}
    for key, value in payload.items():
        if key not in allowed_keys:
            raise HTTPException(status_code=422, detail=f"Unknown setting: {key}")
    session.settings = {**(session.settings or {}), **payload}
    await session_service.session.commit()
    await session_service.session.refresh(session)
    merged = {**_default_settings, **(session.settings or {})}
    return {"settings": merged}
