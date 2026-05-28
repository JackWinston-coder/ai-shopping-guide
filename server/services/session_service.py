from uuid import uuid4

import aiosqlite

from server.errors import AppError, ERROR_SESSION_NOT_FOUND
from server.models.session import Session


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
        return [self._row_to_session(row) for row in rows]

    async def get_session(self, user_id: str, session_id: str) -> Session:
        cursor = await self.db.execute(
            "SELECT * FROM sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id),
        )
        row = await cursor.fetchone()
        if row is None:
            raise AppError(ERROR_SESSION_NOT_FOUND, "Session not found", 404, {"session_id": session_id})
        return self._row_to_session(row)

    async def update_session(
        self,
        user_id: str,
        session_id: str,
        title: str | None = None,
        state: str | None = None,
        summary_text: str | None = None,
    ) -> Session:
        await self.get_session(user_id, session_id)
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
            await self.db.execute(
                f"UPDATE sessions SET {', '.join(fields)} WHERE id = ?",
                values,
            )
            await self.db.commit()
        return await self.get_session(user_id, session_id)

    async def delete_session(self, user_id: str, session_id: str) -> None:
        await self.get_session(user_id, session_id)
        await self.db.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        await self.db.execute("DELETE FROM sessions WHERE id = ? AND user_id = ?", (session_id, user_id))
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
