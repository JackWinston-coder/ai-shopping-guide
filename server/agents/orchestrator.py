import json
import logging
from collections.abc import AsyncGenerator

from server.agents.base import BaseAgent
from server.agents.context import ConversationContext
from server.agents.router_agent import RouterAgent
from server.config import settings
from server.models.chat import (
    ConversationState,
    IntentType,
    RouteOutput,
    SSEEvent,
    SSEEventType,
)
from server.services.session_service import SessionService
from server.services.output_validator import OutputValidator
from server.services.summary_service import SummaryService

logger = logging.getLogger(__name__)

INTENT_STATE_MAP = {
    IntentType.PRODUCT_RECOMMEND: ConversationState.RECOMMENDING,
    IntentType.PRODUCT_FILTER: ConversationState.RECOMMENDING,
    IntentType.PRODUCT_COMPARE: ConversationState.COMPARING,
    IntentType.PRODUCT_DETAIL: ConversationState.RECOMMENDING,
    IntentType.CART_ADD: ConversationState.CART_MANAGING,
    IntentType.CART_REMOVE: ConversationState.CART_MANAGING,
    IntentType.CART_UPDATE: ConversationState.CART_MANAGING,
    IntentType.CART_VIEW: ConversationState.CART_MANAGING,
    IntentType.ORDER_PREVIEW: ConversationState.ORDERING,
    IntentType.ORDER_CREATE: ConversationState.ORDERING,
    IntentType.GENERAL_CHAT: ConversationState.IDLE,
}


class AgentOrchestrator:
    def __init__(
        self,
        router_agent: RouterAgent,
        agents: dict[str, BaseAgent],
        session_service: SessionService,
        summary_service: SummaryService,
        output_validator: OutputValidator | None = None,
    ):
        self.router = router_agent
        self.agents = agents
        self.session_service = session_service
        self.summary_service = summary_service
        self.output_validator = output_validator or OutputValidator()

    async def run(
        self,
        user_message: str,
        context: ConversationContext,
    ) -> AsyncGenerator[SSEEvent, None]:
        route_output = await self._route(user_message, context)

        await self._save_user_message(context.session_id, user_message)

        full_response = []
        product_cards: list[dict] = []
        tool_results: list[dict] = []

        for i, route_result in enumerate(route_output.routes):
            target_agent = self.agents.get(route_result.target_agent)
            if not target_agent:
                yield SSEEvent(
                    type=SSEEventType.ERROR,
                    data={"code": "AGENT_NOT_FOUND", "message": f"Agent {route_result.target_agent} 不存在"},
                )
                continue

            context.metadata["route_params"] = route_result.extracted_params
            context.metadata["intent"] = route_result.intent

            try:
                async for event in target_agent.run(user_message, context):
                    yield event
                    if event.type == SSEEventType.TEXT_DELTA:
                        full_response.append(event.data.get("content", ""))
                    elif event.type == SSEEventType.PRODUCT_CARDS:
                        products = event.data.get("products", [])
                        if isinstance(products, list):
                            product_cards = products
                            context.recent_product_cards = products
                    elif event.type == SSEEventType.TOOL_RESULT:
                        tool_results.append(event.data)
            except Exception as exc:
                logger.error("Agent %s execution error: %s", route_result.target_agent, exc)
                yield SSEEvent(type=SSEEventType.ERROR, data={"code": "AGENT_EXECUTION_ERROR", "message": str(exc)})
                yield SSEEvent(type=SSEEventType.TEXT_DELTA, data={"content": "抱歉，处理您的请求时遇到了问题，请稍后再试。"})

            if route_output.is_multi_intent and i < len(route_output.routes) - 1:
                yield SSEEvent(type=SSEEventType.TEXT_DELTA, data={"content": "\n\n---\n\n"})

        if route_output.routes:
            last_intent = route_output.routes[-1].intent
            await self._update_conversation_state(context, last_intent)

        response_text = "".join(full_response)
        validation = self.output_validator.validate_product_references(response_text, product_cards)
        if not validation.valid:
            logger.warning("Assistant output validation failed: %s", validation.reason)
            yield SSEEvent(
                type=SSEEventType.ERROR,
                data={"code": "OUTPUT_VALIDATION_ERROR", "message": validation.reason},
            )
            response_text = "我需要重新基于已检索到的商品组织推荐，避免引用未确认的商品信息。"
        await self._save_assistant_message(
            context.session_id,
            response_text,
            product_cards=product_cards,
            tool_results=tool_results,
        )

        summary = await self.summary_service.generate_if_needed(context.session_id, self.session_service)
        if summary is not None:
            await self.session_service.update_session(
                context.user_id,
                context.session_id,
                summary_text=summary,
            )

        yield SSEEvent(type=SSEEventType.DONE, data={})

    async def _route(self, user_message: str, context: ConversationContext) -> RouteOutput:
        try:
            return await self.router.route(user_message, context)
        except Exception as exc:
            logger.warning("Router failed, falling back to guide_agent: %s", exc)
            return RouteOutput(
                routes=[
                    {
                        "intent": IntentType.GENERAL_CHAT,
                        "target_agent": "guide_agent",
                        "extracted_params": {"query": user_message},
                        "confidence": 0.0,
                    }
                ],
                is_multi_intent=False,
            )

    async def _update_conversation_state(self, context: ConversationContext, intent: IntentType) -> None:
        new_state = INTENT_STATE_MAP.get(intent, ConversationState.IDLE)
        try:
            await self.session_service.update_session(
                context.user_id,
                context.session_id,
                state=new_state.value,
            )
        except Exception as exc:
            logger.warning("Failed to update conversation state: %s", exc)

    async def _save_user_message(self, session_id: str, content: str) -> None:
        try:
            await self.session_service.add_message(session_id, "user", content)
        except Exception as exc:
            logger.warning("Failed to save user message: %s", exc)

    async def _save_assistant_message(
        self,
        session_id: str,
        content: str,
        product_cards: list[dict] | None = None,
        tool_results: list[dict] | None = None,
    ) -> None:
        if not content.strip() and not product_cards and not tool_results:
            return
        try:
            await self.session_service.add_message(
                session_id,
                "assistant",
                content,
                products_json=json.dumps(product_cards, ensure_ascii=False) if product_cards else None,
                tool_calls_json=json.dumps(tool_results, ensure_ascii=False) if tool_results else None,
            )
        except Exception as exc:
            logger.warning("Failed to save assistant message: %s", exc)
