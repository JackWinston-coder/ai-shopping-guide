import json
import logging

from server.agents.context import ConversationContext
from server.config import settings
from server.llm.zhipu_client import ZhipuClient
from server.models.chat import IntentType, RouteOutput, RouteResult

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

ROUTER_SYSTEM_PROMPT = """你是一个意图识别路由器。你的任务是分析用户消息，识别用户意图，并输出结构化路由结果。

## 可选意图

| 意图 | 说明 | 目标 Agent |
|------|------|-----------|
| product_recommend | 用户想找商品推荐 | guide_agent |
| product_filter | 用户有明确筛选条件 | guide_agent |
| product_compare | 用户想对比多个商品 | guide_agent |
| product_detail | 用户想了解商品详情 | guide_agent |
| cart_add | 用户想加入购物车 | cart_agent |
| cart_remove | 用户想移除购物车商品 | cart_agent |
| cart_update | 用户想修改购物车数量 | cart_agent |
| cart_view | 用户想查看购物车 | cart_agent |
| order_preview | 用户想看订单预览 | order_agent |
| order_create | 用户想确认下单 | order_agent |
| general_chat | 闲聊、追问或模糊意图 | guide_agent |

## 判断规则

1. 如果用户提到"推荐"、"有什么"、"想买"、"找"等词，且不涉及购物车操作 → product_recommend
2. 如果用户提到价格范围、品牌、类目等筛选条件 → product_filter
3. 如果用户提到"A和B"、"哪个好"、"对比" → product_compare
4. 如果用户提到"详情"、"更多"、"评价" → product_detail
5. 如果用户提到"加入购物车"、"买这个"、"要这个" → cart_add
6. 如果用户提到"删掉"、"不要了"、"移除" → cart_remove
7. 如果用户提到"数量"、"改成"、"再加" → cart_update
8. 如果用户提到"购物车"、"买了什么" → cart_view
9. 如果用户提到"结算"、"总价"、"结账" → order_preview
10. 如果用户提到"下单"、"确认购买"、"付款" → order_create
11. 其他情况 → general_chat

## 混合意图处理

当用户一条消息中包含多个不同意图时（例如"推荐一个面霜，然后把刚才那个耳机加入购物车"），需要在 routes 数组中输出多个路由结果，按用户提到的顺序排列。

判断是否为混合意图：
- 用户消息中同时包含推荐类意图和购物车/订单操作意图 → 混合意图
- 用户消息中同时包含购物车操作和下单意图 → 混合意图
- 同一类别的多个操作（如"把第一个和第二个都加入购物车"）→ 单意图 cart_add，不是混合意图
- 推荐类意图的细化追问（如"推荐面霜，不要含酒精的"）→ 单意图 product_filter，不是混合意图

## 注意

- 只输出路由结果，不要回答用户问题
- 提取用户消息中的关键参数（类目、品牌、价格、排除条件等）
- 如果意图模糊，优先归为 general_chat
- 置信度低于 0.6 时归为 general_chat
- 混合意图时，每个意图的 confidence 独立评估"""


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
