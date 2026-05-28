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

        if positive_reviews:
            chunks.append(
                ProductChunk(
                    id=f"{product.product_id}:review_positive",
                    product_id=product.product_id,
                    chunk_type="review_positive",
                    text=f"{product.title}\n好评：{'；'.join(positive_reviews)}",
                    metadata={**base_metadata, "chunk_type": "review_positive"},
                )
            )

        if negative_reviews:
            chunks.append(
                ProductChunk(
                    id=f"{product.product_id}:review_negative",
                    product_id=product.product_id,
                    chunk_type="review_negative",
                    text=f"{product.title}\n差评/缺点：{'；'.join(negative_reviews)}",
                    metadata={**base_metadata, "chunk_type": "review_negative"},
                )
            )

        return chunks

    def chunk_products(self, products: list[Product]) -> list[ProductChunk]:
        chunks: list[ProductChunk] = []
        for product in products:
            chunks.extend(self.chunk_product(product))
        return chunks

