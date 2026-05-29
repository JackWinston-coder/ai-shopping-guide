from uuid import uuid4

import aiosqlite

from server.errors import AppError, ERROR_SESSION_NOT_FOUND
from server.models.session import Session, SessionMessage


class SessionService:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def create_session(self, user_id: str, title: str = "新对话") -> Session:
        session_id = f"s_{uuid4().hex}"
        await self.db.execute(
            "INSERT INTO sessions (id, user_id, title) VALUES (?, ?, ?)",
            (session_id, user_id, title),
        )
        await self.db.commit()
        return await self.get_session(user_id, session_id)

    async def list_sessions(self, user_id: str) -> list[Session]:
        cursor = await self.db.execute(
            "SELECT * FROM sessions WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        )
        rows = await cursor.fetchall()
        sessions = [self._row_to_session(row) for row in rows]
        for session in sessions:
            session.messages = await self.list_messages(session.id)
        return sessions

    async def get_session(self, user_id: str, session_id: str) -> Session:
        cursor = await self.db.execute(
            "SELECT * FROM sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        )
        row = await cursor.fetchone()
        if row is None:
            raise AppError(ERROR_SESSION_NOT_FOUND, "Session not found", 404, {"session_id": session_id})
        session = self._row_to_session(row)
        session.messages = await self.list_messages(session.id)
        return session

    async def get_session_by_id(self, session_id: str) -> Session | None:
        cursor = await self.db.execute(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        session = self._row_to_session(row)
        session.messages = await self.list_messages(session.id)
        return session

    async def list_messages(self, session_id: str) -> list[SessionMessage]:
        cursor = await self.db.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        )
        rows = await cursor.fetchall()
        return [
            SessionMessage(
                id=row["id"],
                session_id=row["session_id"],
                role=row["role"],
                content=row["content"],
                products_json=row["products_json"],
                tool_calls_json=row["tool_calls_json"],
                tool_call_id=row["tool_call_id"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        products_json: str | None = None,
        tool_calls_json: str | None = None,
        tool_call_id: str | None = None,
    ) -> None:
        message_id = f"m_{uuid4().hex}"
        await self.db.execute(
            "INSERT INTO messages (id, session_id, role, content, products_json, tool_calls_json, tool_call_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (message_id, session_id, role, content, products_json, tool_calls_json, tool_call_id),
        )
        await self.db.commit()

    async def update_session(
        self,
        user_id: str,
        session_id: str,
        title: str | None = None,
        state: str | None = None,
        summary_text: str | None = None,
    ) -> Session:
        fields: list[str] = []
        values: list = []
        if title is not None:
            fields.append("title = ?")
            values.append(title)
        if state is not None:
            fields.append("state = ?")
            values.append(state)
        if summary_text is not None:
            fields.append("summary_text = ?")
            values.append(summary_text)
        if fields:
            fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(session_id)
            values.append(user_id)
            cursor = await self.db.execute(
                f"UPDATE sessions SET {', '.join(fields)} WHERE id = ? AND user_id = ?",
                values,
            )
            await self.db.commit()
            if cursor.rowcount == 0:
                raise AppError(ERROR_SESSION_NOT_FOUND, "Session not found", 404, {"session_id": session_id})
        return await self.get_session(user_id, session_id)

    async def delete_session(self, user_id: str, session_id: str) -> None:
        cursor = await self.db.execute("DELETE FROM sessions WHERE id = ? AND user_id = ?", (session_id, user_id))
        if cursor.rowcount == 0:
            raise AppError(ERROR_SESSION_NOT_FOUND, "Session not found", 404, {"session_id": session_id})
        await self.db.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        await self.db.commit()

    @staticmethod
    def _row_to_session(row: aiosqlite.Row) -> Session:
        return Session(
            id=row["id"],
            user_id=row["user_id"],
            title=row["title"],
            state=row["state"],
            summary_text=row["summary_text"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
