import json
import logging
from collections.abc import AsyncGenerator

from server.agents.base import BaseAgent, ToolRegistry
from server.agents.context import ConversationContext
from server.config import settings
from server.llm.zhipu_client import ZhipuClient
from server.models.chat import SSEEvent, SSEEventType
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

CART_SYSTEM_PROMPT = """你是「AI Shopping Guide」的购物车管理助手。你的职责是准确执行用户的购物车操作。

## 核心原则

1. **所有购物车操作必须通过工具执行**：绝不模拟、编造或猜测操作结果。
2. **精确匹配商品**：当用户说"把第二个加入购物车"时，根据对话上下文中最近展示的商品列表确定具体商品。
3. **操作后确认**：每次操作后告知用户操作结果（成功/失败）。
4. **不编造购物车内容**：如果不确定购物车状态，调用 cart_view 查看后再回答。

## 商品引用解析规则

当用户使用指代词时，按以下规则解析：
- "第一个/第二个/第三个" → 对话中最近出现的商品卡片列表中的对应位置
- "刚才那个" → 对话中最近提到的商品
- 商品名/品牌名 → 按名称匹配

## 回复风格

- 简洁确认操作结果
- 如有异常（商品不存在、库存不足等）明确告知
- 适当提示下一步操作（如"还需要其他商品吗？"）"""


class CartAgent(BaseAgent):
    agent_name = "cart_agent"

    def __init__(self, llm_client: ZhipuClient):
        tool_registry = ToolRegistry()
        tool_registry.register("cart_add", CART_ADD_SCHEMA, cart_add)
        tool_registry.register("cart_remove", CART_REMOVE_SCHEMA, cart_remove)
        tool_registry.register("cart_update_quantity", CART_UPDATE_QUANTITY_SCHEMA, cart_update_quantity)
        tool_registry.register("cart_view", CART_VIEW_SCHEMA, cart_view)
        super().__init__(llm_client=llm_client, tool_registry=tool_registry)

    async def run(self, user_message: str, context: ConversationContext) -> AsyncGenerator[SSEEvent, None]:
        messages = self._build_messages(user_message, context)

        while True:
            try:
                response = await self.llm_client.chat(
                    messages=messages,
                    tools=self.tool_registry.get_schemas(),
                    model=settings.zhipu_llm_model_fast,
                    temperature=0.1,
                    max_tokens=1024,
                )
            except Exception as exc:
                logger.error("CartAgent LLM call failed: %s", exc)
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

                messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(tool_result, ensure_ascii=False)})

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

    async def _execute_tool(self, name: str, arguments: dict, context: ConversationContext) -> dict:
        try:
            result = await self.tool_registry.execute(name, arguments, context=context)
            return result if isinstance(result, dict) else {"success": True, "data": result}
        except Exception as exc:
            logger.warning("Tool %s execution error: %s", name, exc)
            return {"success": False, "error": str(exc)}
