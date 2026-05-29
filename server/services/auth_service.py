from datetime import datetime, timedelta, timezone
from uuid import uuid4

import aiosqlite
from jose import jwt
from passlib.hash import bcrypt

from server.config import settings
from server.errors import AppError, ERROR_AUTH
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

    async def register(
        self,
        phone: str | None,
        email: str | None,
        password: str,
        nickname: str | None = None,
    ) -> tuple[User, str]:
        if not phone and not email:
            raise AppError(ERROR_AUTH, "phone or email is required", 422)
        if len(password) < 6:
            raise AppError(ERROR_AUTH, "password must be at least 6 characters", 422)

        identifier = phone or email
        column = "phone" if phone else "email"
        query = "SELECT id FROM users WHERE phone = ?" if column == "phone" else "SELECT id FROM users WHERE email = ?"
        cursor = await self.db.execute(query, (identifier,))
        if await cursor.fetchone() is not None:
            raise AppError(ERROR_AUTH, f"{column} already registered", 409)

        user_id = f"u_{uuid4().hex}"
        user_nickname = nickname or identifier
        password_hash = bcrypt.hash(password)
        await self.db.execute(
            "INSERT INTO users (id, phone, email, password_hash, nickname) VALUES (?, ?, ?, ?, ?)",
            (user_id, phone, email, password_hash, user_nickname),
        )
        await self.db.commit()
        user = User(id=user_id, phone=phone, email=email, nickname=user_nickname)
        return user, self.create_token(user.id)

    async def login(
        self,
        phone: str | None,
        email: str | None,
        password: str,
    ) -> tuple[User, str]:
        if not phone and not email:
            raise AppError(ERROR_AUTH, "phone or email is required", 422)

        identifier = phone or email
        column = "phone" if phone else "email"
        query = "SELECT * FROM users WHERE phone = ?" if column == "phone" else "SELECT * FROM users WHERE email = ?"
        cursor = await self.db.execute(query, (identifier,))
        row = await cursor.fetchone()
        if row is None:
            raise AppError(ERROR_AUTH, "invalid credentials", 401)
        if not bcrypt.verify(password, row["password_hash"]):
            raise AppError(ERROR_AUTH, "invalid credentials", 401)
        user = self._row_to_user(row)
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
