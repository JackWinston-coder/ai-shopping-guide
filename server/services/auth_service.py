from datetime import datetime, timedelta, timezone
from uuid import uuid4

import aiosqlite
from jose import jwt

from server.config import settings
from server.models.user import User


class AuthService:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    @staticmethod
    def decode_token(token: str) -> str:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return str(payload["sub"])

    @staticmethod
    def create_token(user_id: str) -> str:
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.jwt_expire_days)
        return jwt.encode({"sub": user_id, "exp": expires_at}, settings.jwt_secret, algorithm="HS256")

    async def login(self, phone: str | None, email: str | None, nickname: str | None) -> tuple[User, str]:
        identifier_field = "phone" if phone else "email"
        identifier = phone or email
        if not identifier:
            raise ValueError("phone or email is required")

        allowed_columns = {"phone": "phone", "email": "email"}
        column = allowed_columns[identifier_field]
        cursor = await self.db.execute(
            f"SELECT * FROM users WHERE {column} = ?",
            (identifier,),
        )
        row = await cursor.fetchone()
        if row is None:
            user_id = f"u_{uuid4().hex}"
            user_nickname = nickname or identifier
            await self.db.execute(
                "INSERT INTO users (id, phone, email, nickname) VALUES (?, ?, ?, ?)",
                (user_id, phone, email, user_nickname),
            )
            await self.db.commit()
            user = User(id=user_id, phone=phone, email=email, nickname=user_nickname)
        else:
            user = self._row_to_user(row)
            if nickname and nickname != user.nickname:
                await self.db.execute(
                    "UPDATE users SET nickname = ? WHERE id = ?",
                    (nickname, user.id),
                )
                await self.db.commit()
                user = User(
                    id=user.id,
                    phone=user.phone,
                    email=user.email,
                    nickname=nickname,
                    avatar=user.avatar,
                    created_at=user.created_at,
                )

        return user, self.create_token(user.id)

    async def get_user(self, user_id: str) -> User | None:
        cursor = await self.db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        return self._row_to_user(row) if row else None

    @staticmethod
    def _row_to_user(row: aiosqlite.Row) -> User:
        return User(
            id=row["id"],
            phone=row["phone"],
            email=row["email"],
            nickname=row["nickname"],
            avatar=row["avatar"],
            created_at=row["created_at"],
        )
