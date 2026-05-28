import aiosqlite
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from server.api.deps import get_current_user, get_db, get_product_service
from server.models.user import User
from server.services.cart_service import CartService
from server.services.product_service import ProductService

router = APIRouter(prefix="/api/cart", tags=["cart"])


class CartAddRequest(BaseModel):
    product_id: str
    sku_id: str | None = None
    quantity: int = Field(1, ge=1)


class CartUpdateRequest(BaseModel):
    quantity: int = Field(..., ge=1)


def _cart_payload(items):
    return {
        "items": items,
        "total_count": sum(item.quantity for item in items),
        "total_price": sum(item.price * item.quantity for item in items),
    }


@router.get("")
async def view_cart(
    user: User = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
    product_service: ProductService = Depends(get_product_service),
):
    items = await CartService(db, product_service).list_items(user.id)
    return _cart_payload(items)


@router.post("/items")
async def add_item(
    payload: CartAddRequest,
    user: User = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
    product_service: ProductService = Depends(get_product_service),
):
    item = await CartService(db, product_service).add_item(user.id, payload.product_id, payload.sku_id, payload.quantity)
    return item


@router.patch("/items/{item_id}")
async def update_item(
    item_id: str,
    payload: CartUpdateRequest,
    user: User = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
    product_service: ProductService = Depends(get_product_service),
):
    return await CartService(db, product_service).update_quantity(user.id, item_id, payload.quantity)


@router.delete("/items/{item_id}")
async def remove_item(
    item_id: str,
    user: User = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
    product_service: ProductService = Depends(get_product_service),
):
    await CartService(db, product_service).remove_item(user.id, item_id)
    return {"ok": True}

