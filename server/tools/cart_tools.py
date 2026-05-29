import json
import logging
from typing import Any

from server.agents.context import ConversationContext
from server.services.cart_service import CartService
from server.services.product_service import ProductService

logger = logging.getLogger(__name__)


def _get_product_service(product_service: ProductService | None, context: ConversationContext | None = None) -> ProductService:
    if product_service is not None:
        return product_service
    if context is not None and context.product_service is not None:
        return context.product_service
    return ProductService()


async def _get_cart_service(cart_service: CartService | None, product_service: ProductService | None, context: ConversationContext | None = None) -> CartService | None:
    if cart_service is not None:
        return cart_service
    if context is not None and context.cart_service is not None:
        return context.cart_service
    from server.db.database import _db_connection
    if _db_connection is None:
        return None
    return CartService(_db_connection, _get_product_service(product_service, context))


async def cart_add(
    product_id: str,
    sku_id: str | None = None,
    quantity: int = 1,
    context: ConversationContext | None = None,
    cart_service: CartService | None = None,
    product_service: ProductService | None = None,
) -> dict:
    ps = _get_product_service(product_service, context)
    cs = await _get_cart_service(cart_service, ps, context)
    if cs is None:
        return {"success": False, "error": "数据库未连接"}
    if context is None:
        return {"success": False, "error": "缺少上下文"}
    try:
        item = await cs.add_item(context.user_id, product_id, sku_id, quantity)
        return {
            "success": True,
            "message": f"已将 {item.title} 加入购物车",
            "cart_item": {
                "id": item.id,
                "title": item.title,
                "sku": item.sku_label,
                "price": item.price,
                "quantity": item.quantity,
            },
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


async def cart_remove(
    item_id: str,
    context: ConversationContext | None = None,
    cart_service: CartService | None = None,
    product_service: ProductService | None = None,
) -> dict:
    ps = _get_product_service(product_service, context)
    cs = await _get_cart_service(cart_service, ps, context)
    if cs is None:
        return {"success": False, "error": "数据库未连接"}
    if context is None:
        return {"success": False, "error": "缺少上下文"}
    try:
        await cs.remove_item(context.user_id, item_id)
        return {"success": True, "message": "已从购物车移除"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


async def cart_update_quantity(
    item_id: str,
    quantity: int,
    context: ConversationContext | None = None,
    cart_service: CartService | None = None,
    product_service: ProductService | None = None,
) -> dict:
    ps = _get_product_service(product_service, context)
    cs = await _get_cart_service(cart_service, ps, context)
    if cs is None:
        return {"success": False, "error": "数据库未连接"}
    if context is None:
        return {"success": False, "error": "缺少上下文"}
    try:
        item = await cs.update_quantity(context.user_id, item_id, quantity)
        return {
            "success": True,
            "message": f"已将 {item.title} 数量修改为 {quantity}",
            "cart_item": {
                "id": item.id,
                "title": item.title,
                "sku": item.sku_label,
                "price": item.price,
                "quantity": item.quantity,
            },
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


async def cart_view(
    context: ConversationContext | None = None,
    cart_service: CartService | None = None,
    product_service: ProductService | None = None,
) -> dict:
    ps = _get_product_service(product_service, context)
    cs = await _get_cart_service(cart_service, ps, context)
    if cs is None:
        return {"success": False, "error": "数据库未连接"}
    if context is None:
        return {"success": False, "error": "缺少上下文"}
    try:
        items = await cs.list_items(context.user_id)
        return {
            "success": True,
            "items": [
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "title": item.title,
                    "sku": item.sku_label,
                    "price": item.price,
                    "quantity": item.quantity,
                    "image_path": item.image_path,
                }
                for item in items
            ],
            "total_count": sum(item.quantity for item in items),
            "total_price": sum(item.price * item.quantity for item in items),
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


CART_ADD_SCHEMA = {
    "type": "function",
    "function": {
        "name": "cart_add",
        "description": "将指定商品的某个SKU加入购物车。当用户说'加入购物车'、'买这个'、'要这个'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "商品ID",
                },
                "sku_id": {
                    "type": "string",
                    "description": "SKU ID。如果用户未指定规格，留空即可，系统将自动选择默认第一个SKU。",
                },
                "quantity": {
                    "type": "integer",
                    "default": 1,
                    "description": "数量",
                },
            },
            "required": ["product_id"],
        },
    },
}

CART_REMOVE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "cart_remove",
        "description": "从购物车中移除指定商品。当用户说'删掉'、'不要了'、'移除'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "string",
                    "description": "购物车项ID",
                },
            },
            "required": ["item_id"],
        },
    },
}

CART_UPDATE_QUANTITY_SCHEMA = {
    "type": "function",
    "function": {
        "name": "cart_update_quantity",
        "description": "修改购物车中某个商品的数量。当用户说'数量改成X'、'再加一个'、'少买一个'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "string",
                    "description": "购物车项ID",
                },
                "quantity": {
                    "type": "integer",
                    "description": "新的数量（不是增量，是最终数量）",
                },
            },
            "required": ["item_id", "quantity"],
        },
    },
}

CART_VIEW_SCHEMA = {
    "type": "function",
    "function": {
        "name": "cart_view",
        "description": "查看当前购物车内容。当用户说'看看购物车'、'我买了什么'时使用。",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
}
