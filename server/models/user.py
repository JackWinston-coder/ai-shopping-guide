from pydantic import BaseModel


class User(BaseModel):
    id: str
    phone: str | None = None
    email: str | None = None
    nickname: str
    avatar: str | None = None
    created_at: str | None = None
