"""API routes for the integrated terminal (PTY)."""

from __future__ import annotations

import asyncio
import fcntl
import json
import logging
import os
import pty
import struct
import termios
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/shell", tags=["shell"])


class ShellSession:
    """Manages a single PTY shell process."""

    def __init__(self, shell_id: str, shell_path: str = "/bin/bash") -> None:
        self.shell_id = shell_id
        self.shell_path = shell_path
        self.master_fd: int | None = None
        self.pid: int | None = None
        self._read_task: asyncio.Task[None] | None = None
        self._callbacks: list[Callable[[str], None]] = []
        self._closed = False

    def start(self) -> None:
        """Fork a PTY and start the shell process."""
        master, slave = pty.openpty()
        self.master_fd = master
        pid = os.fork()
        if pid == 0:
            # Child process
            os.setsid()
            os.dup2(slave, 0)
            os.dup2(slave, 1)
            os.dup2(slave, 2)
            os.close(master)
            os.close(slave)
            os.execv(self.shell_path, [self.shell_path])
        else:
            # Parent process
            os.close(slave)
            self.pid = pid
            self._read_task = asyncio.create_task(self._read_loop())

    def add_callback(self, callback: Callable[[str], None]) -> None:
        """Register a callback for output data."""
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[str], None]) -> None:
        """Unregister a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _notify(self, data: str) -> None:
        """Notify all registered callbacks with output data."""
        for cb in list(self._callbacks):
            try:
                cb(data)
            except Exception:
                logger.exception("Shell callback error")

    async def _read_loop(self) -> None:
        """Read output from the PTY master fd and broadcast."""
        loop = asyncio.get_running_loop()
        while not self._closed and self.master_fd is not None:
            try:
                data = await loop.run_in_executor(None, os.read, self.master_fd, 4096)
                if not data:
                    break
                text = data.decode("utf-8", errors="replace")
                self._notify(text)
            except OSError:
                break
            except Exception:
                logger.exception("Shell read error")
                break

    def write(self, data: str) -> None:
        """Write data to the PTY."""
        if self._closed or self.master_fd is None:
            raise RuntimeError("Shell is not running")
        os.write(self.master_fd, data.encode("utf-8"))

    def resize(self, cols: int, rows: int) -> None:
        """Resize the PTY terminal dimensions."""
        if self.master_fd is None:
            raise RuntimeError("Shell is not running")
        size = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, size)

    def stop(self) -> None:
        """Terminate the shell process and clean up."""
        self._closed = True
        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = None
        if self.pid is not None:
            try:
                os.kill(self.pid, 15)  # SIGTERM
            except ProcessLookupError:
                pass
            self.pid = None


class ShellManager:
    """Manages all active shell sessions."""

    def __init__(self) -> None:
        self._shells: dict[str, ShellSession] = {}
        self._counter = 0

    def create(self) -> str:
        """Create a new shell session and return its ID."""
        self._counter += 1
        shell_id = f"shell-{self._counter}"
        # Detect user's preferred shell
        shell_path = os.environ.get("SHELL", "/bin/bash")
        session = ShellSession(shell_id, shell_path)
        session.start()
        self._shells[shell_id] = session
        return shell_id

    def get(self, shell_id: str) -> ShellSession | None:
        """Retrieve a shell session by ID."""
        return self._shells.get(shell_id)

    def remove(self, shell_id: str) -> bool:
        """Stop and remove a shell session."""
        session = self._shells.pop(shell_id, None)
        if session is None:
            return False
        session.stop()
        return True


shell_manager = ShellManager()


@router.post("/start")
async def start_shell() -> dict[str, Any]:
    """Start a new shell session and return its ID."""
    shell_id = shell_manager.create()
    return {"shell_id": shell_id, "status": "started"}


@router.post("/{shell_id}/input")
async def shell_input(shell_id: str, payload: dict[str, Any]) -> dict[str, str]:
    """Send input to a running shell."""
    session = shell_manager.get(shell_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Shell not found")
    data = payload.get("data", "")
    try:
        session.write(data)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": "sent"}


@router.post("/{shell_id}/resize")
async def shell_resize(shell_id: str, payload: dict[str, Any]) -> dict[str, str]:
    """Resize the PTY terminal dimensions."""
    session = shell_manager.get(shell_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Shell not found")
    cols = payload.get("cols", 80)
    rows = payload.get("rows", 24)
    try:
        session.resize(cols, rows)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": "resized"}


@router.post("/{shell_id}/stop")
async def stop_shell(shell_id: str) -> dict[str, str]:
    """Stop a shell session."""
    if not shell_manager.remove(shell_id):
        raise HTTPException(status_code=404, detail="Shell not found")
    return {"status": "stopped"}


@router.websocket("/ws/{shell_id}")
async def shell_websocket(websocket: WebSocket, shell_id: str) -> None:
    """WebSocket endpoint for streaming shell I/O."""
    session = shell_manager.get(shell_id)
    if session is None:
        await websocket.close(code=4004, reason="Shell not found")
        return

    await websocket.accept()

    def on_output(data: str) -> None:
        asyncio.create_task(_send_output(websocket, data))

    async def _send_output(ws: WebSocket, data: str) -> None:
        try:
            await ws.send_text(data)
        except Exception:
            pass

    session.add_callback(on_output)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            msg_type = msg.get("type")
            if msg_type == "input":
                data = msg.get("data", "")
                session.write(data)
            elif msg_type == "resize":
                cols = msg.get("cols", 80)
                rows = msg.get("rows", 24)
                session.resize(cols, rows)
    except WebSocketDisconnect:
        pass
    finally:
        session.remove_callback(on_output)
