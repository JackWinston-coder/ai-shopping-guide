from pydantic import BaseModel, Field


class SessionMessage(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    products_json: str | None = None
    tool_calls_json: str | None = None
    tool_call_id: str | None = None
    created_at: str | None = None


class Session(BaseModel):
    id: str
    user_id: str
    title: str = "新对话"
    state: str = "idle"
    summary_text: str | None = None
    messages: list[SessionMessage] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None
