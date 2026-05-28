from typing import Annotated

import aiosqlite
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from server.db.database import get_connection
from server.errors import AppError, ERROR_AUTH
from server.models.user import User
from server.services.auth_service import AuthService
from server.services.product_service import ProductService
from server.services.rag_service import RagService

security = HTTPBearer(auto_error=False)

_product_service_instance: ProductService | None = None
_rag_service_instance: RagService | None = None


def get_product_service() -> ProductService:
    global _product_service_instance
    if _product_service_instance is None:
        _product_service_instance = ProductService()
    return _product_service_instance


def get_rag_service() -> RagService:
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RagService(product_service=get_product_service())
    return _rag_service_instance


async def get_db():
    async for db in get_connection():
        yield db


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[aiosqlite.Connection, Depends(get_db)],
) -> User:
    if credentials is None:
        raise AppError(ERROR_AUTH, "Missing bearer token", 401)
    try:
        user_id = AuthService.decode_token(credentials.credentials)
    except JWTError as exc:
        raise AppError(ERROR_AUTH, "Invalid bearer token", 401) from exc
    user = await AuthService(db).get_user(user_id)
    if user is None:
        raise AppError(ERROR_AUTH, "User not found", 401)
    return user
