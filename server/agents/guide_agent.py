import json
import logging
from collections.abc import AsyncGenerator

from server.agents.base import BaseAgent, ToolRegistry
from server.agents.context import ConversationContext
from server.config import settings
from server.llm.zhipu_client import ZhipuClient
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

GUIDE_SYSTEM_PROMPT = """你是「AI Shopping Guide」的智能导购助手。你的职责是帮助用户找到最合适的商品。

## 核心原则

1. **只推荐知识库中存在的商品**：你必须通过 search_products 工具检索商品，绝不能编造商品。
2. **价格和SKU必须来自工具返回的结构化数据**：不得编造、修改或推测价格、库存、优惠和SKU信息。
3. **检索无结果时诚实告知**：如果检索不到合适的商品，告诉用户并建议补充或修改条件。
4. **主动引导**：当用户需求模糊时，主动追问以细化需求。

## 工具使用规则

- 用户需要推荐商品 → 调用 search_products
- 用户需要筛选商品 → 调用 search_products（带过滤参数）
- 用户想了解商品详情 → 调用 get_product_detail
- 用户想对比商品 → 调用 compare_products
- 用户想加入购物车 → 提示用户点击商品卡片上的"加入购物车"按钮，或告诉用户你将为其添加
- 不要在未调用工具的情况下回答关于具体商品的问题

## 回复风格

- 友好、专业、简洁
- 推荐商品时给出理由，结合用户需求说明为什么适合
- 可以适当使用emoji增加亲和力
- 回复中引用商品时，必须使用工具返回的准确信息

## 幻觉防控

- 绝不编造不存在的商品
- 绝不编造价格、优惠、库存、SKU
- 绝不编造用户评价或FAQ内容
- 如果不确定某个信息，明确告知用户"我暂时无法确认这个信息"
- 商品卡片数据只来自工具返回的结构化结果"""


class GuideAgent(BaseAgent):
    agent_name = "guide_agent"

    def __init__(self, llm_client: ZhipuClient):
        tool_registry = ToolRegistry()
        tool_registry.register("search_products", SEARCH_PRODUCTS_SCHEMA, search_products)
        tool_registry.register("get_product_detail", GET_PRODUCT_DETAIL_SCHEMA, get_product_detail)
        tool_registry.register("compare_products", COMPARE_PRODUCTS_SCHEMA, compare_products)
        super().__init__(llm_client=llm_client, tool_registry=tool_registry)

    async def run(self, user_message: str, context: ConversationContext) -> AsyncGenerator[SSEEvent, None]:
        messages = self._build_messages(user_message, context)

        while True:
            try:
                response = await self.llm_client.chat(
                    messages=messages,
                    tools=self.tool_registry.get_schemas(),
                    model=settings.zhipu_llm_model,
                    temperature=0.7,
                    max_tokens=2048,
                )
            except Exception as exc:
                logger.error("GuideAgent LLM call failed: %s", exc)
                yield SSEEvent(type=SSEEventType.ERROR, data={"code": "LLM_ERROR", "message": str(exc)})
                break

            choice = response.choices[0]
            assistant_message = choice.message

            if assistant_message.content:
                yield SSEEvent(type=SSEEventType.TEXT_DELTA, data={"content": assistant_message.content})

            if not assistant_message.tool_calls:
                break

            messages.append({"role": "assistant", "content": assistant_message.content, "tool_calls": [tc.model_dump() for tc in assistant_message.tool_calls]})

            for tool_call in assistant_message.tool_calls:
                func = tool_call.function
                name = func.name
                try:
                    arguments = json.loads(func.arguments) if isinstance(func.arguments, str) else func.arguments
                except json.JSONDecodeError:
                    arguments = {}

                tool_result = await self._execute_tool(name, arguments, context)

                yield SSEEvent(type=SSEEventType.TOOL_RESULT, data={"tool": name, "result": tool_result})

                if name == "search_products" and tool_result.get("products"):
                    yield SSEEvent(type=SSEEventType.PRODUCT_CARDS, data={"products": tool_result["products"]})

                messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(tool_result, ensure_ascii=False)})

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

    async def _execute_tool(self, name: str, arguments: dict, context: ConversationContext) -> dict:
        try:
            result = await self.tool_registry.execute(name, arguments, context=context)
            return result if isinstance(result, dict) else {"success": True, "data": result}
        except Exception as exc:
            logger.warning("Tool %s execution error: %s", name, exc)
            return {"success": False, "error": str(exc)}
