import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

import aiosqlite

from server.agents.cart_agent import CartAgent
from server.agents.context import ContextBuilder
from server.agents.guide_agent import GuideAgent
from server.agents.order_agent import OrderAgent
from server.agents.orchestrator import AgentOrchestrator
from server.agents.router_agent import RouterAgent
from server.api.deps import get_current_user, get_db, get_product_service, get_rag_service
from server.llm.zhipu_client import ZhipuClient
from server.models.chat import ChatStreamRequest, SSEEvent, SSEEventType
from server.models.user import User
from server.services.cart_service import CartService
from server.services.output_validator import OutputValidator
from server.services.product_service import ProductService
from server.services.rag_service import RagService
from server.services.session_service import SessionService
from server.services.order_service import OrderService
from server.services.summary_service import SummaryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _get_llm_client(request: Request) -> ZhipuClient:
    if not hasattr(request.app.state, "llm_client") or request.app.state.llm_client is None:
        request.app.state.llm_client = ZhipuClient()
    return request.app.state.llm_client


def _get_orchestrator(request: Request, db: aiosqlite.Connection) -> AgentOrchestrator:
    if not hasattr(request.app.state, "orchestrator") or request.app.state.orchestrator is None:
        llm_client = _get_llm_client(request)
        product_service = get_product_service(request)
        router_agent = RouterAgent(llm_client)
        agents = {
            "guide_agent": GuideAgent(llm_client),
            "cart_agent": CartAgent(llm_client),
            "order_agent": OrderAgent(llm_client),
        }
        session_service = SessionService(db)
        summary_service = SummaryService(llm_client)
        request.app.state.orchestrator = AgentOrchestrator(
            router_agent=router_agent,
            agents=agents,
            session_service=session_service,
            summary_service=summary_service,
            output_validator=OutputValidator(),
        )
    request.app.state.orchestrator.session_service = SessionService(db)
    return request.app.state.orchestrator


@router.post("/stream")
async def chat_stream(
    payload: ChatStreamRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
    product_service: ProductService = Depends(get_product_service),
    rag_service: RagService = Depends(get_rag_service),
):
    orchestrator = _get_orchestrator(request, db)
    llm_client = _get_llm_client(request)
    cart_service = CartService(db, product_service)
    order_service = OrderService(db, product_service)
    session_service = SessionService(db)
    context_builder = ContextBuilder(session_service, cart_service, product_service)

    async def event_generator():
        try:
            context = await context_builder.build(user.id, payload.session_id)
            context.product_service = product_service
            context.cart_service = cart_service
            context.rag_service = rag_service
            context.order_service = order_service
            yield SSEEvent(
                type=SSEEventType.SESSION,
                data={"session_id": context.session_id},
            ).format()
            user_message = payload.message
            if payload.image_url:
                image_summary = await llm_client.image_understand(
                    payload.image_url,
                    "请提取图片中的商品类别、外观特征、颜色、风格、适用场景和可用于检索的关键词，输出一段简洁中文描述。",
                )
                user_message = f"{payload.message}\n\n图片理解结果：{image_summary}"

            async for event in orchestrator.run(
                user_message=user_message,
                context=context,
            ):
                yield event.format()

        except Exception as exc:
            logger.error("Chat stream error: %s", exc)
            error_event = SSEEvent(
                type=SSEEventType.ERROR,
                data={"code": "INTERNAL_ERROR", "message": str(exc)},
            )
            yield error_event.format()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
