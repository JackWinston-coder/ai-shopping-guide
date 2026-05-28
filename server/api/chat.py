import logging

from fastapi import APIRouter, Depends
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
from server.services.product_service import ProductService
from server.services.rag_service import RagService
from server.services.session_service import SessionService
from server.services.summary_service import SummaryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

_llm_client: ZhipuClient | None = None
_orchestrator: AgentOrchestrator | None = None


def _get_llm_client() -> ZhipuClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = ZhipuClient()
    return _llm_client


def _get_orchestrator(db: aiosqlite.Connection) -> AgentOrchestrator:
    global _orchestrator
    if _orchestrator is not None:
        _orchestrator.session_service = SessionService(db)
        return _orchestrator

    llm_client = _get_llm_client()
    product_service = get_product_service()

    router_agent = RouterAgent(llm_client)
    agents = {
        "guide_agent": GuideAgent(llm_client),
        "cart_agent": CartAgent(llm_client),
        "order_agent": OrderAgent(llm_client),
    }

    session_service = SessionService(db)
    summary_service = SummaryService(llm_client)

    _orchestrator = AgentOrchestrator(
        router_agent=router_agent,
        agents=agents,
        session_service=session_service,
        summary_service=summary_service,
    )
    return _orchestrator


@router.post("/stream")
async def chat_stream(
    payload: ChatStreamRequest,
    user: User = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
    product_service: ProductService = Depends(get_product_service),
    rag_service: RagService = Depends(get_rag_service),
):
    orchestrator = _get_orchestrator(db)
    cart_service = CartService(db, product_service)
    session_service = SessionService(db)
    context_builder = ContextBuilder(session_service, cart_service, product_service)

    async def event_generator():
        try:
            context = await context_builder.build(user.id, payload.session_id)

            async for event in orchestrator.run(
                user_message=payload.message,
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
