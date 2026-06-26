"""API routes for configuration presets."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.preset_service import PresetService

router = APIRouter(prefix="/api/presets", tags=["presets"])


def _get_preset_service(db: AsyncSession = Depends(get_db)) -> PresetService:
    return PresetService(db)


@router.get("")
async def list_presets(
    preset_service: PresetService = Depends(_get_preset_service),
) -> dict[str, Any]:
    """Return all presets."""
    presets = await preset_service.list_presets()
    return {"presets": [preset_service.to_dict(p) for p in presets]}


@router.post("")
async def create_preset(
    payload: dict[str, Any],
    preset_service: PresetService = Depends(_get_preset_service),
) -> dict[str, Any]:
    """Create a preset from {name, settings}."""
    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        raise HTTPException(status_code=422, detail="name is required")
    try:
        preset = await preset_service.create_preset(name, payload.get("settings") or {})
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"preset": preset_service.to_dict(preset)}


@router.put("/{preset_id}")
async def update_preset(
    preset_id: str,
    payload: dict[str, Any],
    preset_service: PresetService = Depends(_get_preset_service),
) -> dict[str, Any]:
    """Update a preset's name and/or settings."""
    try:
        preset = await preset_service.update_preset(
            preset_id,
            name=payload.get("name"),
            settings=payload.get("settings"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if preset is None:
        raise HTTPException(status_code=404, detail="Preset not found")
    return {"preset": preset_service.to_dict(preset)}


@router.delete("/{preset_id}")
async def delete_preset(
    preset_id: str,
    preset_service: PresetService = Depends(_get_preset_service),
) -> dict[str, Any]:
    """Delete a preset."""
    deleted = await preset_service.delete_preset(preset_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Preset not found")
    return {"deleted": True}
