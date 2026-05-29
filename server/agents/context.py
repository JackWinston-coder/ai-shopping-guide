from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from server.models.chat import ConversationState
from server.models.cart import CartItem
from server.models.product import Product
from server.services.cart_service import CartService
from server.services.product_service import ProductService
from server.services.session_service import SessionService

if TYPE_CHECKING:
    from server.services.rag_service import RagService
    from server.services.order_service import OrderService

logger = logging.getLogger(__name__)


@dataclass
class ConversationContext:
    user_id: str
    session_id: str
    recent_history: str = ""
    recent_product_cards: list[dict] = field(default_factory=list)
    cart_summary: str = "购物车为空"
    cart_items: list[CartItem] = field(default_factory=list)
    conversation_state: ConversationState = ConversationState.IDLE
    summary_text: str | None = None
    metadata: dict = field(default_factory=dict)
    product_service: ProductService | None = None
    cart_service: CartService | None = None
    rag_service: RagService | None = None
    order_service: OrderService | None = None


class ContextBuilder:
    def __init__(
        self,
        session_service: SessionService,
        cart_service: CartService,
        product_service: ProductService,
    ):
        self.session_service = session_service
        self.cart_service = cart_service
        self.product_service = product_service

    async def build(self, user_id: str, session_id: str | None = None) -> ConversationContext:
        if session_id is None:
            session = await self.session_service.create_session(user_id)
        else:
            try:
                session = await self.session_service.get_session(user_id, session_id)
            except Exception:
                session = await self.session_service.create_session(user_id)

        messages = await self._load_messages(session.id)
        recent_history = self._format_history(messages[-10:])
        recent_products = self._extract_recent_products(messages)
        cart_items = await self.cart_service.list_items(user_id)
        cart_summary = self._format_cart_summary(cart_items)

        state = ConversationState(session.state) if session.state else ConversationState.IDLE

        return ConversationContext(
            user_id=user_id,
            session_id=session.id,
            recent_history=recent_history,
            recent_product_cards=recent_products,
            cart_summary=cart_summary,
            cart_items=cart_items,
            conversation_state=state,
            summary_text=session.summary_text,
        )

    async def _load_messages(self, session_id: str) -> list[dict]:
        messages = await self.session_service.list_messages(session_id)
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "products_json": msg.products_json,
                "tool_calls_json": msg.tool_calls_json,
            }
            for msg in messages
        ]

    @staticmethod
    def _format_history(messages: list[dict]) -> str:
        if not messages:
            return ""
        lines = []
        for msg in messages[-10:]:
            role_label = "用户" if msg["role"] == "user" else "助手"
            content = msg["content"][:200] if len(msg["content"]) > 200 else msg["content"]
            lines.append(f"{role_label}：{content}")
        return "\n".join(lines)

    def _extract_recent_products(self, messages: list[dict]) -> list[dict]:
        for msg in reversed(messages):
            products_json = msg.get("products_json")
            if products_json:
                try:
                    products = json.loads(products_json)
                    if isinstance(products, list) and products:
                        return products[:10]
                except json.JSONDecodeError:
                    pass
        return []

    @staticmethod
    def _format_cart_summary(items: list[CartItem]) -> str:
        if not items:
            return "购物车为空"
        lines = [f"- {item.title} ({item.sku_label}) x{item.quantity} = ¥{item.price * item.quantity}" for item in items]
        total = sum(item.price * item.quantity for item in items)
        return f"购物车共{len(items)}件商品，合计¥{total}：\n" + "\n".join(lines)
