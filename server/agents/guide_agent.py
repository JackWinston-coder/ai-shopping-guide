import logging

from server.agents.base import BaseAgent, ToolRegistry
from server.agents.context import ConversationContext
from server.config import settings
from server.llm.zhipu_client import ZhipuClient
from server.llm.prompts import load_prompt
from server.models.chat import SSEEvent, SSEEventType
from server.tools.guide_tools import (
    COMPARE_PRODUCTS_SCHEMA,
    GET_PRODUCT_DETAIL_SCHEMA,
    SEARCH_PRODUCTS_SCHEMA,
    compare_products,
    get_product_detail,
    search_products,
)

logger = logging.getLogger(__name__)

GUIDE_SYSTEM_PROMPT = load_prompt("guide_system.md")


class GuideAgent(BaseAgent):
    agent_name = "guide_agent"
    llm_model = settings.zhipu_llm_model
    llm_temperature = 0.7
    llm_max_tokens = 2048

    def __init__(self, llm_client: ZhipuClient):
        tool_registry = ToolRegistry()
        tool_registry.register("search_products", SEARCH_PRODUCTS_SCHEMA, search_products)
        tool_registry.register("get_product_detail", GET_PRODUCT_DETAIL_SCHEMA, get_product_detail)
        tool_registry.register("compare_products", COMPARE_PRODUCTS_SCHEMA, compare_products)
        super().__init__(llm_client=llm_client, tool_registry=tool_registry)

    def _build_messages(self, user_message: str, context: ConversationContext) -> list[dict]:
        messages = [{"role": "system", "content": GUIDE_SYSTEM_PROMPT}]

        if context.summary_text:
            messages.append({"role": "system", "content": f"之前的对话摘要：{context.summary_text}"})

        if context.cart_summary and context.cart_summary != "购物车为空":
            messages.append({"role": "system", "content": f"当前购物车状态：{context.cart_summary}"})

        if context.recent_product_cards:
            product_ids = [p.get("product_id", "") for p in context.recent_product_cards[:5]]
            if product_ids:
                messages.append({"role": "system", "content": f"最近展示的商品ID：{', '.join(product_ids)}"})

        messages.append({"role": "user", "content": user_message})
        return messages

    async def _on_tool_result(self, name: str, result: dict, context: ConversationContext):
        if name == "search_products" and result.get("products"):
            yield SSEEvent(type=SSEEventType.PRODUCT_CARDS, data={"products": result["products"]})
