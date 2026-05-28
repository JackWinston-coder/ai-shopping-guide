import aiosqlite
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from server.api.deps import get_current_user, get_db
from server.models.user import User
from server.services.session_service import SessionService

router = APIRouter(prefix="/api/chat/sessions", tags=["sessions"])


class SessionCreateRequest(BaseModel):
    title: str = "新对话"


class SessionUpdateRequest(BaseModel):
    title: str | None = None
    state: str | None = None
    summary_text: str | None = None


@router.post("")
async def create_session(
    payload: SessionCreateRequest,
    user: User = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    return await SessionService(db).create_session(user.id, payload.title)


@router.get("")
async def list_sessions(
    user: User = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    items = await SessionService(db).list_sessions(user.id)
    total = len(items)
    return {"items": items[offset : offset + limit], "total": total, "limit": limit, "offset": offset}


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    return await SessionService(db).get_session(user.id, session_id)


@router.patch("/{session_id}")
async def update_session(
    session_id: str,
    payload: SessionUpdateRequest,
    user: User = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    return await SessionService(db).update_session(
        user.id,
        session_id,
        title=payload.title,
        state=payload.state,
        summary_text=payload.summary_text,
    )


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    await SessionService(db).delete_session(user.id, session_id)
    return {"ok": True}
