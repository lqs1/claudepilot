"""Business logic for global settings management."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GlobalSetting

_DEFAULT_SETTINGS: dict[str, Any] = {
    "model": "claude-sonnet-4-20250514",
    "effort": "normal",
    "permission_mode": "acceptEdits",
    "tools_enabled": True,
}


class SettingService:
    """Service for global settings CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_global_settings(self) -> dict[str, Any]:
        """Return all global settings merged from DB with hardcoded defaults."""
        result = await self.session.execute(select(GlobalSetting))
        rows = result.scalars().all()
        settings = _DEFAULT_SETTINGS.copy()
        for row in rows:
            settings[row.key] = row.value
        return settings

    async def set_global_settings(self, updates: dict[str, Any]) -> dict[str, Any]:
        """Update global settings in the database."""
        for key, value in updates.items():
            existing = await self.session.get(GlobalSetting, key)
            if existing is not None:
                existing.value = value
            else:
                self.session.add(GlobalSetting(key=key, value=value))
        await self.session.commit()
        return await self.get_global_settings()

    async def init_default_settings(self) -> None:
        """Ensure default settings exist in the database."""
        for key, value in _DEFAULT_SETTINGS.items():
            existing = await self.session.get(GlobalSetting, key)
            if existing is None:
                self.session.add(GlobalSetting(key=key, value=value))
        await self.session.commit()
