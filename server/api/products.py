from fastapi import APIRouter, Depends, Query

from server.api.deps import get_product_service
from server.services.product_service import ProductService

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("")
async def list_products(
    category: str | None = None,
    keyword: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    product_service: ProductService = Depends(get_product_service),
):
    products, total = product_service.list_products(category=category, keyword=keyword, limit=limit, offset=offset)
    return {"items": products, "total": total, "limit": limit, "offset": offset}


@router.get("/{product_id}")
async def get_product(product_id: str, product_service: ProductService = Depends(get_product_service)):
    return product_service.get_product(product_id)

