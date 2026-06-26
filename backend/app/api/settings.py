"""API routes for global and session settings."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.session_service import SessionService
from app.services.setting_service import SettingService


router = APIRouter(prefix="/api/settings", tags=["settings"])

_ALLOWED_KEYS = {"model", "effort", "permission_mode", "tools_enabled", "max_turns"}


def _get_session_service(db: AsyncSession = Depends(get_db)) -> SessionService:
    return SessionService(db)


def _get_setting_service(db: AsyncSession = Depends(get_db)) -> SettingService:
    return SettingService(db)


@router.get("")
async def get_settings(
    setting_service: SettingService = Depends(_get_setting_service),
) -> dict[str, Any]:
    """Return the global default settings."""
    settings = await setting_service.get_global_settings()
    return {"settings": settings}


@router.put("")
async def update_settings(
    payload: dict[str, Any],
    setting_service: SettingService = Depends(_get_setting_service),
) -> dict[str, Any]:
    """Update the global default settings."""
    for key in payload:
        if key not in _ALLOWED_KEYS:
            raise HTTPException(status_code=422, detail=f"Unknown setting: {key}")
    settings = await setting_service.set_global_settings(payload)
    return {"settings": settings}


@router.get("/session/{session_id}")
async def get_session_settings(
    session_id: str,
    session_service: SessionService = Depends(_get_session_service),
    setting_service: SettingService = Depends(_get_setting_service),
) -> dict[str, Any]:
    """Return session-specific settings merged with global defaults."""
    session = await session_service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    global_settings = await setting_service.get_global_settings()
    overrides = session.settings or {}
    merged = {**global_settings, **overrides}
    return {"settings": merged}


@router.put("/session/{session_id}")
async def update_session_settings(
    session_id: str,
    payload: dict[str, Any],
    session_service: SessionService = Depends(_get_session_service),
    setting_service: SettingService = Depends(_get_setting_service),
) -> dict[str, Any]:
    """Update session-specific settings overrides."""
    session = await session_service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    for key in payload:
        if key not in _ALLOWED_KEYS:
            raise HTTPException(status_code=422, detail=f"Unknown setting: {key}")
    session.settings = {**(session.settings or {}), **payload}
    await session_service.session.commit()
    await session_service.session.refresh(session)
    global_settings = await setting_service.get_global_settings()
    merged = {**global_settings, **(session.settings or {})}
    return {"settings": merged}
