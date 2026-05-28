import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Database initialized")
    yield
    await close_db()
    logger.info("Database connection closed")


app = FastAPI(
    title="AI Shopping Guide API",
    version="0.1.0",
    lifespan=lifespan,
)

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
