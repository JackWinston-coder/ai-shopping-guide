import json
import logging
from typing import Any

from server.agents.context import ConversationContext
from server.services.order_service import OrderService
from server.services.product_service import ProductService

logger = logging.getLogger(__name__)


async def order_preview(
    address: str | None = None,
    context: ConversationContext | None = None,
    order_service: OrderService | None = None,
    product_service: ProductService | None = None,
) -> dict:
    if product_service is None:
        from server.api.deps import get_product_service
        product_service = get_product_service()
    if order_service is None:
        from server.db.database import _db_connection
        if _db_connection is None:
            return {"success": False, "error": "数据库未连接"}
        order_service = OrderService(_db_connection, product_service)
    if context is None:
        return {"success": False, "error": "缺少上下文"}
    try:
        preview = await order_service.preview(context.user_id)
        return {
            "success": True,
            "items": [
                {
                    "product_id": item.product_id,
                    "title": item.title,
                    "sku": item.sku_label,
                    "price": item.price,
                    "quantity": item.quantity,
                }
                for item in preview["items"]
            ],
            "total_price": preview["total_price"],
            "total_count": preview["total_count"],
            "address": address,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


async def order_create(
    address: str,
    context: ConversationContext | None = None,
    order_service: OrderService | None = None,
    product_service: ProductService | None = None,
) -> dict:
    if product_service is None:
        from server.api.deps import get_product_service
        product_service = get_product_service()
    if order_service is None:
        from server.db.database import _db_connection
        if _db_connection is None:
            return {"success": False, "error": "数据库未连接"}
        order_service = OrderService(_db_connection, product_service)
    if context is None:
        return {"success": False, "error": "缺少上下文"}
    try:
        order = await order_service.create_order(context.user_id, address)
        return {
            "success": True,
            "order_id": order.id,
            "order_no": order.order_no,
            "total_price": order.total_price,
            "status": order.status,
            "message": f"订单创建成功！订单号：{order.order_no}",
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


ORDER_PREVIEW_SCHEMA = {
    "type": "function",
    "function": {
        "name": "order_preview",
        "description": "生成订单预览信息，包含商品汇总、金额计算。当用户说'结算'、'看看总价'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "收货地址。如果用户未提供，提示用户提供。",
                },
            },
            "required": [],
        },
    },
}

ORDER_CREATE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "order_create",
        "description": "确认下单，创建模拟订单。当用户确认购买时使用。下单前必须先调用 order_preview。",
        "parameters": {
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "收货地址",
                },
            },
            "required": ["address"],
        },
    },
}
