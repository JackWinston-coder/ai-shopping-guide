import aiosqlite
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from server.api.deps import get_current_user, get_db, get_product_service
from server.models.user import User
from server.services.order_service import OrderService
from server.services.product_service import ProductService

router = APIRouter(prefix="/api/orders", tags=["orders"])


class OrderCreateRequest(BaseModel):
    address: str = Field(..., min_length=1)


@router.post("/preview")
async def preview_order(
    user: User = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
    product_service: ProductService = Depends(get_product_service),
):
    return await OrderService(db, product_service).preview(user.id)


@router.post("")
async def create_order(
    payload: OrderCreateRequest,
    user: User = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
    product_service: ProductService = Depends(get_product_service),
):
    return await OrderService(db, product_service).create_order(user.id, payload.address)


@router.get("")
async def list_orders(
    user: User = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
    product_service: ProductService = Depends(get_product_service),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    items = await OrderService(db, product_service).list_orders(user.id)
    total = len(items)
    return {"items": items[offset : offset + limit], "total": total, "limit": limit, "offset": offset}


@router.get("/{order_id}")
async def get_order(
    order_id: str,
    user: User = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
    product_service: ProductService = Depends(get_product_service),
):
    return await OrderService(db, product_service).get_order(user.id, order_id)

