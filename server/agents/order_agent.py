import logging

from server.agents.base import BaseAgent, ToolRegistry
from server.agents.context import ConversationContext
from server.llm.zhipu_client import ZhipuClient
from server.llm.prompts import load_prompt
from server.tools.cart_tools import CART_VIEW_SCHEMA, cart_view
from server.tools.order_tools import ORDER_CREATE_SCHEMA, ORDER_PREVIEW_SCHEMA, order_create, order_preview

logger = logging.getLogger(__name__)

ORDER_SYSTEM_PROMPT = load_prompt("order_system.md")


class OrderAgent(BaseAgent):
    agent_name = "order_agent"

    def __init__(self, llm_client: ZhipuClient):
        tool_registry = ToolRegistry()
        tool_registry.register("order_preview", ORDER_PREVIEW_SCHEMA, order_preview)
        tool_registry.register("order_create", ORDER_CREATE_SCHEMA, order_create)
        tool_registry.register("cart_view", CART_VIEW_SCHEMA, cart_view)
        super().__init__(llm_client=llm_client, tool_registry=tool_registry)

    def _build_messages(self, user_message: str, context: ConversationContext) -> list[dict]:
        messages = [{"role": "system", "content": ORDER_SYSTEM_PROMPT}]

        if context.cart_summary:
            messages.append({"role": "system", "content": f"当前购物车状态：{context.cart_summary}"})

        messages.append({"role": "user", "content": user_message})
        return messages
