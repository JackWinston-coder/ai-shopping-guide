import json
import logging
from typing import Any

from server.agents.context import ConversationContext
from server.services.product_service import ProductService
from server.services.rag_service import RagService

logger = logging.getLogger(__name__)


async def search_products(
    query: str,
    category: str | None = None,
    brand: str | None = None,
    price_min: float | None = None,
    price_max: float | None = None,
    exclude_keywords: list[str] | None = None,
    top_k: int = 5,
    context: ConversationContext | None = None,
    rag_service: RagService | None = None,
) -> dict:
    if rag_service is None:
        from server.api.deps import get_rag_service
        rag_service = get_rag_service()
    results = await rag_service.search(
        query=query,
        category=category,
        brand=brand,
        price_min=price_min,
        price_max=price_max,
        exclude_keywords=exclude_keywords,
        top_k=top_k,
    )
    products = []
    for result in results:
        product = result.product
        products.append({
            "product_id": product.product_id,
            "title": product.title,
            "brand": product.brand,
            "category": product.category,
            "sub_category": product.sub_category,
            "base_price": product.base_price,
            "image_path": product.image_path,
            "skus": [sku.model_dump() for sku in product.skus],
            "score": result.score,
        })
    return {"products": products}


async def get_product_detail(
    product_id: str,
    context: ConversationContext | None = None,
    product_service: ProductService | None = None,
) -> dict:
    if product_service is None:
        from server.api.deps import get_product_service
        product_service = get_product_service()
    try:
        product = product_service.get_product(product_id)
    except Exception:
        return {"success": False, "error": f"商品 {product_id} 不存在"}
    rag = product.rag_knowledge
    rating_avg = 0.0
    reviews = rag.get("user_reviews", [])
    if reviews:
        rating_avg = sum(r.get("rating", 0) for r in reviews) / len(reviews)
    return {
        "success": True,
        "product_id": product.product_id,
        "title": product.title,
        "brand": product.brand,
        "category": product.category,
        "sub_category": product.sub_category,
        "base_price": product.base_price,
        "image_path": product.image_path,
        "skus": [sku.model_dump() for sku in product.skus],
        "rating_avg": round(rating_avg, 1),
        "marketing_description": rag.get("marketing_description", ""),
        "faq": rag.get("official_faq", []),
        "reviews_summary": {
            "positive": [r for r in reviews if r.get("rating", 0) >= 4],
            "negative": [r for r in reviews if r.get("rating", 0) <= 2],
        },
    }


async def compare_products(
    product_ids: list[str],
    dimensions: list[str] | None = None,
    context: ConversationContext | None = None,
    product_service: ProductService | None = None,
) -> dict:
    if product_service is None:
        from server.api.deps import get_product_service
        product_service = get_product_service()
    products = []
    for pid in product_ids[:4]:
        try:
            product = product_service.get_product(pid)
            rag = product.rag_knowledge
            rating_avg = 0.0
            reviews = rag.get("user_reviews", [])
            if reviews:
                rating_avg = sum(r.get("rating", 0) for r in reviews) / len(reviews)
            products.append({
                "product_id": product.product_id,
                "title": product.title,
                "brand": product.brand,
                "category": product.category,
                "sub_category": product.sub_category,
                "base_price": product.base_price,
                "image_path": product.image_path,
                "skus": [sku.model_dump() for sku in product.skus],
                "rating_avg": round(rating_avg, 1),
                "marketing_description": rag.get("marketing_description", ""),
            })
        except Exception:
            pass
    if not products:
        return {"success": False, "error": "未找到任何指定商品"}
    return {"success": True, "products": products, "dimensions": dimensions}


SEARCH_PRODUCTS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_products",
        "description": "从商品知识库中检索商品。支持语义搜索和结构化过滤。当用户需要推荐、筛选或查找商品时使用此工具。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "用户的语义查询，如'适合油皮的护肤品'、'降噪耳机'",
                },
                "category": {
                    "type": "string",
                    "enum": ["美妆护肤", "数码电子", "服饰运动", "食品饮料"],
                    "description": "商品类目过滤",
                },
                "brand": {
                    "type": "string",
                    "description": "品牌过滤",
                },
                "price_min": {
                    "type": "number",
                    "description": "最低价格",
                },
                "price_max": {
                    "type": "number",
                    "description": "最高价格",
                },
                "exclude_keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "需要排除的关键词",
                },
                "top_k": {
                    "type": "integer",
                    "default": 5,
                    "description": "返回商品数量",
                },
            },
            "required": ["query"],
        },
    },
}

GET_PRODUCT_DETAIL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_product_detail",
        "description": "获取指定商品的详细信息，包括SKU、价格、评价、FAQ等。当用户想了解某个商品详情时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "商品ID",
                },
            },
            "required": ["product_id"],
        },
    },
}

COMPARE_PRODUCTS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "compare_products",
        "description": "对比多个商品的详细信息，返回结构化对比数据。当用户想对比两个或多个商品时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "product_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要对比的商品ID列表",
                    "minItems": 2,
                    "maxItems": 4,
                },
                "dimensions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "对比维度，如['价格','适用肤质','功效']。不填则对比所有维度。",
                },
            },
            "required": ["product_ids"],
        },
    },
}
