from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, details: dict | None = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "details": exc.details},
    )


async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": detail.get("code", "HTTP_ERROR"),
            "message": detail.get("message", str(exc.detail)),
            "details": detail.get("details", {}),
        },
    )


ERROR_AUTH = "AUTH_ERROR"
ERROR_PRODUCT_NOT_FOUND = "PRODUCT_NOT_FOUND"
ERROR_CART_EMPTY = "CART_EMPTY"
ERROR_CART_ITEM_NOT_FOUND = "CART_ITEM_NOT_FOUND"
ERROR_ORDER_NOT_FOUND = "ORDER_NOT_FOUND"
ERROR_SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
ERROR_VALIDATION = "VALIDATION_ERROR"
