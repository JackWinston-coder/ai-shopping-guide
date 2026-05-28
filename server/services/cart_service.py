from uuid import uuid4

import aiosqlite

from server.errors import AppError, ERROR_CART_ITEM_NOT_FOUND
from server.models.cart import CartItem
from server.services.product_service import ProductService


class CartService:
    def __init__(self, db: aiosqlite.Connection, product_service: ProductService):
        self.db = db
        self.product_service = product_service

    async def list_items(self, user_id: str) -> list[CartItem]:
        cursor = await self.db.execute(
            "SELECT * FROM cart_items WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_item(row) for row in rows]

    async def add_item(self, user_id: str, product_id: str, sku_id: str | None, quantity: int) -> CartItem:
        product, sku = self.product_service.get_default_sku(product_id, sku_id)
        sku_label = " / ".join(f"{key}: {value}" for key, value in sku.properties.items()) or sku.sku_id

        cursor = await self.db.execute(
            "SELECT * FROM cart_items WHERE user_id = ? AND product_id = ? AND sku_id = ?",
            (user_id, product.product_id, sku.sku_id),
        )
        existing = await cursor.fetchone()
        if existing:
            new_quantity = existing["quantity"] + quantity
            await self.db.execute("UPDATE cart_items SET quantity = ? WHERE id = ?", (new_quantity, existing["id"]))
            await self.db.commit()
            return await self.get_item(user_id, existing["id"])

        item_id = f"ci_{uuid4().hex}"
        await self.db.execute(
            """
            INSERT INTO cart_items (id, user_id, product_id, sku_id, title, sku_label, price, quantity, image_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item_id,
                user_id,
                product.product_id,
                sku.sku_id,
                product.title,
                sku_label,
                sku.price,
                quantity,
                product.image_path,
            ),
        )
        await self.db.commit()
        return await self.get_item(user_id, item_id)

    async def get_item(self, user_id: str, item_id: str) -> CartItem:
        cursor = await self.db.execute(
            "SELECT * FROM cart_items WHERE id = ? AND user_id = ?",
            (item_id, user_id),
        )
        row = await cursor.fetchone()
        if row is None:
            raise AppError(ERROR_CART_ITEM_NOT_FOUND, "Cart item not found", 404, {"item_id": item_id})
        return self._row_to_item(row)

    async def update_quantity(self, user_id: str, item_id: str, quantity: int) -> CartItem:
        await self.get_item(user_id, item_id)
        await self.db.execute(
            "UPDATE cart_items SET quantity = ? WHERE id = ? AND user_id = ?",
            (quantity, item_id, user_id),
        )
        await self.db.commit()
        return await self.get_item(user_id, item_id)

    async def remove_item(self, user_id: str, item_id: str) -> None:
        await self.get_item(user_id, item_id)
        await self.db.execute("DELETE FROM cart_items WHERE id = ? AND user_id = ?", (item_id, user_id))
        await self.db.commit()

    @staticmethod
    def _row_to_item(row: aiosqlite.Row) -> CartItem:
        return CartItem(
            id=row["id"],
            user_id=row["user_id"],
            product_id=row["product_id"],
            sku_id=row["sku_id"],
            title=row["title"],
            sku_label=row["sku_label"],
            price=row["price"],
            quantity=row["quantity"],
            image_path=row["image_path"],
            created_at=row["created_at"],
        )

