from server.api.deps import get_rag_service
from server.services.rag_service import RagService


async def search_products(
    query: str,
    category: str | None = None,
    brand: str | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    exclude_keywords: list[str] | None = None,
    top_k: int | None = None,
    rag_service: RagService | None = None,
) -> dict:
    service = rag_service or get_rag_service()
    results = await service.search(
        query=query,
        category=category,
        brand=brand,
        price_min=price_min,
        price_max=price_max,
        exclude_keywords=exclude_keywords,
        top_k=top_k,
    )
    return {
        "products": [
            {
                "product_id": result.product.product_id,
                "title": result.product.title,
                "brand": result.product.brand,
                "category": result.product.category,
                "sub_category": result.product.sub_category,
                "base_price": result.product.base_price,
                "image_path": result.product.image_path,
                "skus": [sku.model_dump() for sku in result.product.skus],
                "score": result.score,
                "matched_chunk_types": result.matched_chunk_types,
            }
            for result in results
        ]
    }

