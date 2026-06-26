"""ClaudePilot backend application."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.api import filesystem, messages, presets, projects, sessions, settings, shell
from app.database import close_db, init_db
from app.services.setting_service import SettingService
from app.websocket import websocket_manager


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown."""
    await init_db()
    # Initialize default global settings
    from app.database import async_session_maker

    async with async_session_maker() as db_session:
        setting_service = SettingService(db_session)
        await setting_service.init_default_settings()
    yield
    await close_db()


app = FastAPI(
    title="ClaudePilot",
    description="A modern web-based scheduler and visualizer for Claude Code CLI.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(sessions.router)
app.include_router(messages.router)
app.include_router(presets.router)
app.include_router(filesystem.router)
app.include_router(settings.router)
app.include_router(shell.router)


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.websocket("/ws/shell/{shell_id}")
async def shell_websocket_endpoint(websocket: WebSocket, shell_id: str) -> None:
    """WebSocket endpoint for shell streaming."""
    await shell.shell_websocket(websocket, shell_id)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time session updates."""
    await websocket_manager.handle(websocket)
