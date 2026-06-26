"""Business logic for configuration presets.

A preset is a named bundle of session-start settings (a ClaudePilot
value-add). Only keys in ``ALLOWED_SETTING_KEYS`` are kept; anything else is
dropped so a preset can never smuggle in unknown config.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Preset
from app.services.setting_service import ALLOWED_SETTING_KEYS, _DEFAULT_SETTINGS


def sanitize_settings(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Drop any keys that are not part of the allowed setting set."""
    if not raw:
        return {}
    return {k: v for k, v in raw.items() if k in ALLOWED_SETTING_KEYS}


class PresetService:
    """CRUD for presets."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_presets(self) -> list[Preset]:
        """Return all presets ordered by name."""
        result = await self.session.execute(select(Preset).order_by(Preset.name.asc()))
        return list(result.scalars().all())

    async def get_preset(self, preset_id: str) -> Preset | None:
        """Fetch a preset by ID."""
        return await self.session.get(Preset, preset_id)

    async def create_preset(self, name: str, settings: dict[str, Any]) -> Preset:
        """Create a preset. Raises ValueError on empty name or duplicate name."""
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Preset name is required")

        preset = Preset(name=clean_name, settings=sanitize_settings(settings))
        self.session.add(preset)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ValueError(f"A preset named '{clean_name}' already exists") from exc
        await self.session.refresh(preset)
        return preset

    async def update_preset(
        self,
        preset_id: str,
        *,
        name: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> Preset | None:
        """Update a preset's name and/or settings. Returns None if not found."""
        preset = await self.get_preset(preset_id)
        if preset is None:
            return None
        if name is not None:
            clean_name = name.strip()
            if not clean_name:
                raise ValueError("Preset name is required")
            preset.name = clean_name
        if settings is not None:
            preset.settings = sanitize_settings(settings)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ValueError("A preset with that name already exists") from exc
        await self.session.refresh(preset)
        return preset

    async def delete_preset(self, preset_id: str) -> bool:
        """Delete a preset. Returns True if something was removed."""
        preset = await self.get_preset(preset_id)
        if preset is None:
            return False
        await self.session.delete(preset)
        await self.session.commit()
        return True

    @staticmethod
    def to_dict(preset: Preset) -> dict[str, Any]:
        """Serialize a preset to a dictionary, merging defaults for display."""
        return {
            "id": preset.id,
            "name": preset.name,
            "settings": {**_DEFAULT_SETTINGS, **preset.settings},
            "created_at": preset.created_at.isoformat(),
            "updated_at": preset.updated_at.isoformat(),
        }


__all__ = ["PresetService", "sanitize_settings"]
