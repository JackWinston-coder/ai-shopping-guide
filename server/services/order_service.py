import json
from datetime import datetime
from uuid import uuid4

import aiosqlite

from server.errors import AppError, ERROR_CART_EMPTY, ERROR_ORDER_NOT_FOUND
from server.models.order import Order, OrderItem
from server.services.cart_service import CartService
from server.services.product_service import ProductService


class OrderService:
    def __init__(self, db: aiosqlite.Connection, product_service: ProductService):
        self.db = db
        self.cart_service = CartService(db, product_service)

    async def preview(self, user_id: str) -> dict:
        items = await self.cart_service.list_items(user_id)
        if not items:
            raise AppError(ERROR_CART_EMPTY, "Cart is empty", 400)
        total_price = sum(item.price * item.quantity for item in items)
        return {"items": items, "total_price": total_price, "total_count": sum(item.quantity for item in items)}

    async def create_order(self, user_id: str, address: str) -> Order:
        preview = await self.preview(user_id)
        order_id = f"o_{uuid4().hex}"
        order_no = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid4().hex[:6].upper()}"
        order_items = [
            OrderItem(
                product_id=item.product_id,
                sku_id=item.sku_id,
                title=item.title,
                sku_label=item.sku_label,
                price=item.price,
                quantity=item.quantity,
                image_path=item.image_path,
            )
            for item in preview["items"]
        ]
        try:
            await self.db.execute("BEGIN")
            await self.db.execute(
                """
                INSERT INTO orders (id, order_no, user_id, items_json, total_price, address, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    order_no,
                    user_id,
                    json.dumps([item.model_dump() for item in order_items], ensure_ascii=False),
                    preview["total_price"],
                    address,
                    "confirmed",
                ),
            )
            await self.db.execute("DELETE FROM cart_items WHERE user_id = ?", (user_id,))
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        return await self.get_order(user_id, order_id)

    async def list_orders(self, user_id: str) -> list[Order]:
        cursor = await self.db.execute(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_order(row) for row in rows]

    async def get_order(self, user_id: str, order_id: str) -> Order:
        cursor = await self.db.execute(
            "SELECT * FROM orders WHERE id = ? AND user_id = ?",
            (order_id, user_id),
        )
        row = await cursor.fetchone()
        if row is None:
            raise AppError(ERROR_ORDER_NOT_FOUND, "Order not found", 404, {"order_id": order_id})
        return self._row_to_order(row)

    @staticmethod
    def _row_to_order(row: aiosqlite.Row) -> Order:
        items = [OrderItem.model_validate(item) for item in json.loads(row["items_json"])]
        return Order(
            id=row["id"],
            order_no=row["order_no"],
            user_id=row["user_id"],
            items=items,
            total_price=row["total_price"],
            address=row["address"],
            status=row["status"],
            created_at=row["created_at"],
        )

