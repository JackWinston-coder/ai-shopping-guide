import json
from enum import Enum

from pydantic import BaseModel


class SSEEventType(str, Enum):
    SESSION = "session"
    TEXT_DELTA = "text_delta"
    PRODUCT_CARDS = "product_cards"
    TOOL_RESULT = "tool_result"
    DONE = "done"
    ERROR = "error"


class SSEEvent(BaseModel):
    type: SSEEventType
    data: dict

    def format(self) -> str:
        return f"event: {self.type.value}\ndata: {json.dumps(self.data, ensure_ascii=False)}\n\n"


class ChatStreamRequest(BaseModel):
    message: str
    session_id: str | None = None
    image_url: str | None = None


class IntentType(str, Enum):
    PRODUCT_RECOMMEND = "product_recommend"
    PRODUCT_FILTER = "product_filter"
    PRODUCT_COMPARE = "product_compare"
    PRODUCT_DETAIL = "product_detail"
    CART_ADD = "cart_add"
    CART_REMOVE = "cart_remove"
    CART_UPDATE = "cart_update"
    CART_VIEW = "cart_view"
    ORDER_PREVIEW = "order_preview"
    ORDER_CREATE = "order_create"
    GENERAL_CHAT = "general_chat"


class RouteResult(BaseModel):
    intent: IntentType
    target_agent: str
    extracted_params: dict = {}
    confidence: float = 0.0


class RouteOutput(BaseModel):
    routes: list[RouteResult]
    is_multi_intent: bool = False


class ConversationState(str, Enum):
    IDLE = "idle"
    RECOMMENDING = "recommending"
    COMPARING = "comparing"
    CART_MANAGING = "cart_managing"
    ORDERING = "ordering"
