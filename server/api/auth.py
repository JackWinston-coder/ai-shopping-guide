import aiosqlite
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from server.api.deps import get_db
from server.errors import AppError, ERROR_VALIDATION
from server.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    phone: str | None = None
    email: str | None = None
    nickname: str | None = None


@router.post("/login")
async def login(payload: LoginRequest, db: aiosqlite.Connection = Depends(get_db)):
    if not payload.phone and not payload.email:
        raise AppError(ERROR_VALIDATION, "phone or email is required", 422)
    user, token = await AuthService(db).login(payload.phone, payload.email, payload.nickname)
    return {"access_token": token, "token_type": "bearer", "user": user}

