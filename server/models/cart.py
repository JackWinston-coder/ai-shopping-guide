from pydantic import BaseModel


class CartItem(BaseModel):
    id: str
    user_id: str
    product_id: str
    sku_id: str
    title: str
    sku_label: str
    price: float
    quantity: int
    image_path: str | None = None
    created_at: str | None = None
