import logging

from server.agents.base import BaseAgent, ToolRegistry
from server.agents.context import ConversationContext
from server.llm.zhipu_client import ZhipuClient
from server.llm.prompts import load_prompt
from server.tools.cart_tools import (
    CART_ADD_SCHEMA,
    CART_REMOVE_SCHEMA,
    CART_UPDATE_QUANTITY_SCHEMA,
    CART_VIEW_SCHEMA,
    cart_add,
    cart_remove,
    cart_update_quantity,
    cart_view,
)

logger = logging.getLogger(__name__)

CART_SYSTEM_PROMPT = load_prompt("cart_system.md")


class CartAgent(BaseAgent):
    agent_name = "cart_agent"

    def __init__(self, llm_client: ZhipuClient):
        tool_registry = ToolRegistry()
        tool_registry.register("cart_add", CART_ADD_SCHEMA, cart_add)
        tool_registry.register("cart_remove", CART_REMOVE_SCHEMA, cart_remove)
        tool_registry.register("cart_update_quantity", CART_UPDATE_QUANTITY_SCHEMA, cart_update_quantity)
        tool_registry.register("cart_view", CART_VIEW_SCHEMA, cart_view)
        super().__init__(llm_client=llm_client, tool_registry=tool_registry)

    def _build_messages(self, user_message: str, context: ConversationContext) -> list[dict]:
        messages = [{"role": "system", "content": CART_SYSTEM_PROMPT}]

        if context.cart_summary:
            messages.append({"role": "system", "content": f"当前购物车状态：{context.cart_summary}"})

        if context.recent_product_cards:
            product_info = []
            for i, p in enumerate(context.recent_product_cards[:5], 1):
                product_info.append(f"第{i}个：{p.get('title', '未知商品')} (ID: {p.get('product_id', '')})")
            messages.append({"role": "system", "content": "最近展示的商品：\n" + "\n".join(product_info)})

        messages.append({"role": "user", "content": user_message})
        return messages
