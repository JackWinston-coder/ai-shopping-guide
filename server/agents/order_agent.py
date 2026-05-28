import json
import logging
from collections.abc import AsyncGenerator

from server.agents.base import BaseAgent, ToolRegistry
from server.agents.context import ConversationContext
from server.config import settings
from server.llm.zhipu_client import ZhipuClient
from server.models.chat import SSEEvent, SSEEventType
from server.tools.cart_tools import CART_VIEW_SCHEMA, cart_view
from server.tools.order_tools import ORDER_CREATE_SCHEMA, ORDER_PREVIEW_SCHEMA, order_create, order_preview

logger = logging.getLogger(__name__)

ORDER_SYSTEM_PROMPT = """你是「AI Shopping Guide」的订单管理助手。你的职责是引导用户完成下单流程。

## 核心原则

1. **下单前必须预览**：用户确认下单前，必须先调用 order_preview 展示订单汇总。
2. **必须收集地址**：创建订单需要收货地址，如果用户未提供，主动询问。
3. **模拟订单**：这是模拟下单，不涉及真实支付和物流。订单号由系统自动生成。
4. **金额计算由工具完成**：不自行计算金额，所有金额数据来自工具返回。

## 下单流程

1. 用户说"结算/下单" → 调用 cart_view 确认购物车
2. 如果购物车为空 → 提示用户先添加商品
3. 询问收货地址（首版可使用模拟地址）
4. 调用 order_preview 展示订单汇总
5. 用户确认 → 调用 order_create 创建订单
6. 返回订单号和确认信息

## 回复风格

- 清晰展示订单信息（商品、数量、金额）
- 逐步引导，不跳步
- 确认关键信息后再执行操作"""


class OrderAgent(BaseAgent):
    agent_name = "order_agent"

    def __init__(self, llm_client: ZhipuClient):
        tool_registry = ToolRegistry()
        tool_registry.register("order_preview", ORDER_PREVIEW_SCHEMA, order_preview)
        tool_registry.register("order_create", ORDER_CREATE_SCHEMA, order_create)
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
                logger.error("OrderAgent LLM call failed: %s", exc)
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
        messages = [{"role": "system", "content": ORDER_SYSTEM_PROMPT}]

        if context.cart_summary:
            messages.append({"role": "system", "content": f"当前购物车状态：{context.cart_summary}"})

        messages.append({"role": "user", "content": user_message})
        return messages

    async def _execute_tool(self, name: str, arguments: dict, context: ConversationContext) -> dict:
        try:
            result = await self.tool_registry.execute(name, arguments, context=context)
            return result if isinstance(result, dict) else {"success": True, "data": result}
        except Exception as exc:
            logger.warning("Tool %s execution error: %s", name, exc)
            return {"success": False, "error": str(exc)}
