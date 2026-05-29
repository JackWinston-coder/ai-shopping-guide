import json
import logging

from server.agents.context import ConversationContext
from server.config import settings
from server.llm.zhipu_client import ZhipuClient
from server.models.chat import IntentType, RouteOutput, RouteResult
from server.llm.prompts import load_prompt

logger = logging.getLogger(__name__)

ROUTE_INTENT_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "route_intent",
        "description": "分析用户消息，识别意图并输出结构化路由结果",
        "parameters": {
            "type": "object",
            "properties": {
                "routes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "intent": {
                                "type": "string",
                                "enum": [e.value for e in IntentType],
                            },
                            "target_agent": {
                                "type": "string",
                                "enum": ["guide_agent", "cart_agent", "order_agent"],
                            },
                            "extracted_params": {
                                "type": "object",
                                "description": "从用户消息中提取的关键参数",
                            },
                            "confidence": {
                                "type": "number",
                                "description": "置信度 0-1",
                            },
                        },
                        "required": ["intent", "target_agent", "extracted_params", "confidence"],
                    },
                },
                "is_multi_intent": {
                    "type": "boolean",
                    "description": "是否包含多个不同类别的意图",
                },
            },
            "required": ["routes", "is_multi_intent"],
        },
    },
}

ROUTER_SYSTEM_PROMPT = load_prompt("router_system.md")


class RouterAgent:
    def __init__(self, llm_client: ZhipuClient):
        self.llm_client = llm_client

    async def route(self, user_message: str, context: ConversationContext) -> RouteOutput:
        messages = [
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"当前购物车摘要：{context.cart_summary}\n最近对话：{context.recent_history}\n用户消息：{user_message}",
            },
        ]

        try:
            response = await self.llm_client.chat(
                messages=messages,
                tools=[ROUTE_INTENT_TOOL_SCHEMA],
                model=settings.zhipu_llm_model_fast,
                temperature=0.1,
                max_tokens=512,
            )
            choice = response.choices[0]
            if choice.message.tool_calls:
                tool_call = choice.message.tool_calls[0]
                args = json.loads(tool_call.function.arguments) if isinstance(tool_call.function.arguments, str) else tool_call.function.arguments
                return RouteOutput.model_validate(args)
        except Exception as exc:
            logger.warning("Router LLM call failed, falling back to general_chat: %s", exc)

        return RouteOutput(
            routes=[
                RouteResult(
                    intent=IntentType.GENERAL_CHAT,
                    target_agent="guide_agent",
                    extracted_params={"query": user_message},
                    confidence=0.0,
                )
            ],
            is_multi_intent=False,
        )
