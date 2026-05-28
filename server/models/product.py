from pydantic import BaseModel, Field


class ProductSKU(BaseModel):
    sku_id: str
    properties: dict = Field(default_factory=dict)
    price: float


class Product(BaseModel):
    product_id: str
    title: str
    brand: str
    category: str
    sub_category: str
    base_price: float
    image_path: str
    skus: list[ProductSKU] = Field(default_factory=list)
    rag_knowledge: dict = Field(default_factory=dict)

