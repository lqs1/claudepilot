"""Business logic for session management."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Message, Session


class SessionService:
    """Service for session CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_sessions(self, project_id: str) -> list[Session]:
        """Return all sessions for a project ordered by creation time descending."""
        result = await self.session.execute(
            select(Session)
            .where(Session.project_id == project_id)
            .order_by(Session.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_session(self, session_id: str) -> Session | None:
        """Fetch a session by ID."""
        return await self.session.get(Session, session_id)

    async def create_session(
        self,
        project_id: str,
        title: str = "New Session",
        language: str = "zh",
        settings: dict[str, Any] | None = None,
    ) -> Session:
        """Create a new session for a project."""
        session = Session(
            project_id=project_id,
            title=title,
            language=language,
            status="stopped",
            settings=settings,
        )
        self.session.add(session)
        await self.session.commit()
        await self.session.refresh(session)
        return session

    async def update_status(self, session_id: str, status: str) -> Session | None:
        """Update a session's status."""
        session = await self.get_session(session_id)
        if session is None:
            return None
        session.status = status
        await self.session.commit()
        await self.session.refresh(session)
        return session

    async def update_started_at(
        self, session_id: str, started_at: datetime | None
    ) -> Session | None:
        """Update a session's started_at timestamp."""
        session = await self.get_session(session_id)
        if session is None:
            return None
        session.started_at = started_at
        await self.session.commit()
        await self.session.refresh(session)
        return session

    async def add_message(
        self,
        session_id: str,
        *,
        role: str,
        type: str,
        content: str,
        tool_name: str | None = None,
        tool_input: dict[str, Any] | None = None,
        tool_output: str | None = None,
        tool_status: str | None = None,
    ) -> Message:
        """Add a message to a session."""
        message = Message(
            session_id=session_id,
            role=role,
            type=type,
            content=content,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            tool_status=tool_status,
        )
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def list_messages(self, session_id: str) -> list[Message]:
        """Return all messages for a session ordered by creation time.

        Note: the live history read path is :class:`HistoryService`, which reads
        the CLI jsonl. This helper is kept for tests of the legacy Message
        table and is not used by the history UI.
        """
        result = await self.session.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())

    def to_dict(self, session: Session) -> dict[str, Any]:
        """Serialize a session to a dictionary."""
        return {
            "id": session.id,
            "project_id": session.project_id,
            "title": session.title,
            "language": session.language,
            "status": session.status,
            "started_at": session.started_at.isoformat()
            if session.started_at
            else None,
            "settings": session.settings,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        }

    def message_to_dict(self, message: Message) -> dict[str, Any]:
        """Serialize a message to a dictionary."""
        return {
            "id": message.id,
            "session_id": message.session_id,
            "role": message.role,
            "type": message.type,
            "content": message.content,
            "tool_name": message.tool_name,
            "tool_input": message.tool_input,
            "tool_output": message.tool_output,
            "tool_status": message.tool_status,
            "created_at": message.created_at.isoformat(),
        }
