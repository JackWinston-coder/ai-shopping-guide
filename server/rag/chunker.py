from __future__ import annotations

from dataclasses import dataclass

from server.models.product import Product


@dataclass(frozen=True)
class ProductChunk:
    id: str
    product_id: str
    chunk_type: str
    text: str
    metadata: dict


class ProductChunker:
    def chunk_product(self, product: Product) -> list[ProductChunk]:
        chunks: list[ProductChunk] = []
        base_metadata = {
            "product_id": product.product_id,
            "category": product.category,
            "sub_category": product.sub_category,
            "brand": product.brand,
            "base_price": product.base_price,
            "title": product.title,
        }
        knowledge = product.rag_knowledge or {}

        marketing = knowledge.get("marketing_description")
        if marketing:
            chunks.append(
                ProductChunk(
                    id=f"{product.product_id}:marketing",
                    product_id=product.product_id,
                    chunk_type="marketing",
                    text=f"{product.title}\n{marketing}",
                    metadata={**base_metadata, "chunk_type": "marketing"},
                )
            )

        spec_text = self._build_spec_text(product)
        if spec_text:
            chunks.append(
                ProductChunk(
                    id=f"{product.product_id}:spec",
                    product_id=product.product_id,
                    chunk_type="spec",
                    text=f"{product.title}\n{spec_text}",
                    metadata={**base_metadata, "chunk_type": "spec"},
                )
            )

        sku_text = self._build_sku_text(product)
        if sku_text:
            chunks.append(
                ProductChunk(
                    id=f"{product.product_id}:sku",
                    product_id=product.product_id,
                    chunk_type="sku",
                    text=f"{product.title}\n{sku_text}",
                    metadata={**base_metadata, "chunk_type": "sku"},
                )
            )

        for index, item in enumerate(knowledge.get("official_faq") or []):
            question = item.get("question", "")
            answer = item.get("answer", "")
            text = f"{product.title}\n问题：{question}\n回答：{answer}"
            chunks.append(
                ProductChunk(
                    id=f"{product.product_id}:faq:{index}",
                    product_id=product.product_id,
                    chunk_type="faq",
                    text=text,
                    metadata={**base_metadata, "chunk_type": "faq"},
                )
            )

        positive_reviews: list[str] = []
        negative_reviews: list[str] = []
        for review in knowledge.get("user_reviews") or []:
            content = review.get("content", "")
            rating = int(review.get("rating", 0) or 0)
            if rating >= 4:
                positive_reviews.append(content)
            elif rating <= 2:
                negative_reviews.append(content)

        for i, review_text in enumerate(positive_reviews):
            chunks.append(
                ProductChunk(
                    id=f"{product.product_id}:review_positive:{i}",
                    product_id=product.product_id,
                    chunk_type="review_positive",
                    text=f"{product.title}\n好评：{review_text}",
                    metadata={**base_metadata, "chunk_type": "review_positive"},
                )
            )

        for i, review_text in enumerate(negative_reviews):
            chunks.append(
                ProductChunk(
                    id=f"{product.product_id}:review_negative:{i}",
                    product_id=product.product_id,
                    chunk_type="review_negative",
                    text=f"{product.title}\n差评/缺点：{review_text}",
                    metadata={**base_metadata, "chunk_type": "review_negative"},
                )
            )

        return chunks

    @staticmethod
    def _build_spec_text(product: Product) -> str:
        knowledge = product.rag_knowledge or {}
        specs = knowledge.get("specifications") or knowledge.get("specs")
        if not specs:
            return ""
        if isinstance(specs, dict):
            parts = [f"{k}：{v}" for k, v in specs.items() if v]
            return "\n".join(parts)
        if isinstance(specs, list):
            parts = []
            for item in specs:
                if isinstance(item, dict):
                    name = item.get("name") or item.get("key") or item.get("label", "")
                    value = item.get("value") or item.get("val", "")
                    if name and value:
                        parts.append(f"{name}：{value}")
                elif isinstance(item, str):
                    parts.append(item)
            return "\n".join(parts)
        return str(specs) if specs else ""

    @staticmethod
    def _build_sku_text(product: Product) -> str:
        knowledge = product.rag_knowledge or {}
        skus = knowledge.get("skus") or knowledge.get("variants")
        if not skus:
            if product.base_price:
                return f"价格：¥{product.base_price}"
            return ""
        if isinstance(skus, list):
            parts = []
            for sku in skus:
                if isinstance(sku, dict):
                    name = sku.get("name") or sku.get("variant_name") or sku.get("color") or sku.get("size", "")
                    price = sku.get("price") or sku.get("sale_price") or ""
                    if name or price:
                        parts.append(f"{name}：¥{price}" if price else str(name))
                elif isinstance(sku, str):
                    parts.append(sku)
            return "\n".join(parts)
        return ""

    def chunk_products(self, products: list[Product]) -> list[ProductChunk]:
        chunks: list[ProductChunk] = []
        for product in products:
            chunks.extend(self.chunk_product(product))
        return chunks
