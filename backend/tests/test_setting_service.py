"""Unit tests for setting service persistence."""

from __future__ import annotations

from typing import Any

import pytest
import pytest_asyncio

from app.models import GlobalSetting
from app.services.setting_service import SettingService, _DEFAULT_SETTINGS


@pytest_asyncio.fixture
async def setting_service(client: Any) -> SettingService:
    """Provide a SettingService with a fresh in-memory DB."""
    from app.database import async_session_maker

    async with async_session_maker() as session:
        yield SettingService(session)


@pytest.mark.asyncio
async def test_get_global_settings_returns_defaults(
    setting_service: SettingService,
) -> None:
    """Default settings are returned when DB is empty."""
    settings = await setting_service.get_global_settings()
    assert settings == _DEFAULT_SETTINGS


@pytest.mark.asyncio
async def test_set_global_settings_persists_values(
    setting_service: SettingService,
) -> None:
    """Updates are written to the DB and merged with defaults."""
    updates: dict[str, Any] = {"model": "claude-opus-4", "max_turns": 10}
    settings = await setting_service.set_global_settings(updates)

    assert settings["model"] == "claude-opus-4"
    assert settings["max_turns"] == 10
    # Defaults not provided remain intact
    assert settings["effort"] == _DEFAULT_SETTINGS["effort"]
    assert settings["permission_mode"] == _DEFAULT_SETTINGS["permission_mode"]
    assert settings["tools_enabled"] == _DEFAULT_SETTINGS["tools_enabled"]


@pytest.mark.asyncio
async def test_set_global_settings_updates_existing(
    setting_service: SettingService,
) -> None:
    """Updating an existing key modifies the same row."""
    await setting_service.set_global_settings({"model": "claude-opus-4"})
    settings = await setting_service.set_global_settings({"model": "claude-haiku-4"})

    assert settings["model"] == "claude-haiku-4"

    # Only one row for the key
    from sqlalchemy import select

    result = await setting_service.session.execute(
        select(GlobalSetting).where(GlobalSetting.key == "model")
    )
    rows = list(result.scalars().all())
    assert len(rows) == 1
    assert rows[0].value == "claude-haiku-4"


@pytest.mark.asyncio
async def test_init_default_settings_creates_rows(
    setting_service: SettingService,
) -> None:
    """init_default_settings writes missing defaults to the DB."""
    await setting_service.init_default_settings()

    settings = await setting_service.get_global_settings()
    assert settings == _DEFAULT_SETTINGS

    from sqlalchemy import select

    result = await setting_service.session.execute(select(GlobalSetting))
    rows = list(result.scalars().all())
    assert len(rows) == len(_DEFAULT_SETTINGS)


@pytest.mark.asyncio
async def test_init_default_settings_is_idempotent(
    setting_service: SettingService,
) -> None:
    """Running init_default_settings twice does not duplicate rows."""
    await setting_service.init_default_settings()
    await setting_service.init_default_settings()

    from sqlalchemy import select

    result = await setting_service.session.execute(select(GlobalSetting))
    rows = list(result.scalars().all())
    assert len(rows) == len(_DEFAULT_SETTINGS)
