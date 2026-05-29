import logging
import sys
import time
import uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from server.api.auth import router as auth_router
from server.api.cart import router as cart_router
from server.api.chat import router as chat_router
from server.api.health import router as health_router
from server.api.orders import router as orders_router
from server.api.products import router as products_router
from server.api.sessions import router as sessions_router
from server.config import settings
from server.db.database import init_db, close_db
from server.errors import AppError, app_error_handler, http_error_handler

_correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="-")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(correlation_id)s] %(name)s: %(message)s",
    stream=sys.stdout,
)


class CorrelationIdFilter(logging.Filter):
    def filter(self, record):
        record.correlation_id = _correlation_id_var.get("-")
        return True


logging.getLogger().addFilter(CorrelationIdFilter())
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Database initialized")
    try:
        from server.services.rag_service import RagService
        rag = RagService()
        count = await rag.rebuild_index()
        app.state.rag_service = rag
        logger.info("RAG index initialized with %d chunks", count)
    except Exception as e:
        logger.warning("RAG index initialization skipped: %s", e)
    yield
    await close_db()
    logger.info("Database connection closed")


app = FastAPI(
    title="AI Shopping Guide API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", uuid.uuid4().hex[:12])
    _correlation_id_var.set(correlation_id)
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    response = await call_next(request)
    logger.info(
        "%s %s -> %s",
        request.method,
        request.url.path,
        response.status_code,
    )
    return response


_rate_limit_store: dict[str, list[float]] = {}


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/chat/stream"):
        client_ip = request.client.host if request.client else "unknown"
        key = f"{client_ip}:{request.url.path}"
        now = time.time()
        window = 60
        max_requests = 20
        timestamps = _rate_limit_store.get(key, [])
        timestamps = [ts for ts in timestamps if now - ts < window]
        if len(timestamps) >= max_requests:
            return JSONResponse(
                status_code=429,
                content={"code": "RATE_LIMIT", "message": "请求过于频繁，请稍后再试"},
            )
        timestamps.append(now)
        _rate_limit_store[key] = timestamps
    return await call_next(request)


app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(HTTPException, http_error_handler)

cors_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(products_router)
app.include_router(cart_router)
app.include_router(orders_router)
app.include_router(sessions_router)
app.include_router(chat_router)
app.mount("/data", StaticFiles(directory="data"), name="static-data")


@app.get("/")
async def root():
    return {
        "name": "ai-shopping-guide",
        "status": "ok",
        "env": settings.app_env,
    }
