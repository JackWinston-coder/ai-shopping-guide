from pydantic import BaseModel


class OrderItem(BaseModel):
    product_id: str
    sku_id: str
    title: str
    sku_label: str
    price: float
    quantity: int
    image_path: str | None = None


class Order(BaseModel):
    id: str
    order_no: str
    user_id: str
    items: list[OrderItem]
    total_price: float
    address: str
    status: str = "confirmed"
    created_at: str | None = None
