import json
from functools import cached_property
from pathlib import Path

from server.config import settings
from server.errors import AppError, ERROR_PRODUCT_NOT_FOUND
from server.models.product import Product


def _sanitize_image_path(image_path: str) -> str:
    if ".." in Path(image_path).parts:
        return ""
    resolved = Path(image_path)
    if resolved.is_absolute():
        return ""
    return image_path


class ProductService:
    def __init__(self, data_root: str | None = None):
        self.data_root = Path(data_root or settings.product_data_path)

    @cached_property
    def products(self) -> list[Product]:
        items: list[Product] = []
        for path in sorted(self.data_root.glob("*/data/*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            product = Product.model_validate(data)
            product.image_path = _sanitize_image_path(product.image_path)
            items.append(product)
        return items

    @cached_property
    def _product_index(self) -> dict[str, Product]:
        return {p.product_id: p for p in self.products}

    def list_products(
        self,
        category: str | None = None,
        keyword: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Product], int]:
        products = self.products
        if category:
            products = [product for product in products if product.category == category]
        if keyword:
            lowered = keyword.lower()
            products = [
                product
                for product in products
                if lowered in product.title.lower()
                or lowered in product.brand.lower()
                or lowered in product.sub_category.lower()
            ]
        total = len(products)
        return products[offset : offset + limit], total

    def get_product(self, product_id: str) -> Product:
        product = self._product_index.get(product_id)
        if product is None:
            raise AppError(ERROR_PRODUCT_NOT_FOUND, "Product not found", 404, {"product_id": product_id})
        return product

    def get_default_sku(self, product_id: str, sku_id: str | None = None):
        product = self.get_product(product_id)
        if sku_id:
            for sku in product.skus:
                if sku.sku_id == sku_id:
                    return product, sku
            raise AppError(ERROR_PRODUCT_NOT_FOUND, "SKU not found", 404, {"sku_id": sku_id})
        if not product.skus:
            raise AppError(ERROR_PRODUCT_NOT_FOUND, "Product has no SKU", 404, {"product_id": product_id})
        return product, product.skus[0]

