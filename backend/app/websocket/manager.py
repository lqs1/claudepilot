"""WebSocket connection and broadcasting management."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from app.services.claude_manager import ClaudeSessionManager, session_manager

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manage WebSocket connections and broadcast Claude events."""

    def __init__(self, manager: ClaudeSessionManager) -> None:
        self.manager = manager
        self._connections: dict[str, set[WebSocket]] = {}
        manager.add_callback(self._on_claude_event)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()

    async def handle(self, websocket: WebSocket) -> None:
        """Handle a single WebSocket connection."""
        await self.connect(websocket)
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    message = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                await self._handle_message(websocket, message)
        except WebSocketDisconnect:
            self._unsubscribe_all(websocket)

    async def _handle_message(
        self, websocket: WebSocket, message: dict[str, Any]
    ) -> None:
        msg_type = message.get("type")
        session_id = message.get("session_id")

        if msg_type == "subscribe" and session_id:
            self._subscribe(session_id, websocket)
        elif msg_type == "unsubscribe" and session_id:
            self._unsubscribe(session_id, websocket)

    def _subscribe(self, session_id: str, websocket: WebSocket) -> None:
        self._connections.setdefault(session_id, set()).add(websocket)
        logger.debug("WebSocket subscribed to session %s", session_id)

    def _unsubscribe(self, session_id: str, websocket: WebSocket) -> None:
        subscribers = self._connections.get(session_id)
        if subscribers:
            subscribers.discard(websocket)
            if not subscribers:
                self._connections.pop(session_id, None)

    def _unsubscribe_all(self, websocket: WebSocket) -> None:
        for session_id in list(self._connections.keys()):
            self._unsubscribe(session_id, websocket)

    def _on_claude_event(self, session_id: str, payload: dict[str, Any]) -> None:
        message = {"type": "claude_event", "session_id": session_id, "data": payload}
        asyncio.create_task(self._broadcast(session_id, message))

    async def broadcast_status(self, session_id: str, status: str) -> None:
        await self._broadcast(
            session_id,
            {"type": "status", "session_id": session_id, "data": {"status": status}},
        )

    async def _broadcast(self, session_id: str, message: dict[str, Any]) -> None:
        subscribers = self._connections.get(session_id)
        if not subscribers:
            return
        data = json.dumps(message)
        disconnected: list[WebSocket] = []
        for websocket in subscribers:
            try:
                await websocket.send_text(data)
            except RuntimeError:
                disconnected.append(websocket)
        for websocket in disconnected:
            self._unsubscribe(session_id, websocket)


# Application-level singleton.
websocket_manager = WebSocketManager(session_manager)
