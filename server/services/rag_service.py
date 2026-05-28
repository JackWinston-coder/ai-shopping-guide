from dataclasses import dataclass
import re

from server.config import DOMAIN_RULES, settings
from server.models.product import Product
from server.rag.chunker import ProductChunker
from server.rag.embedder import Embedder
from server.rag.reranker import Reranker
from server.rag.retriever import Retriever
from server.rag.vector_store import VectorStore
from server.services.product_service import ProductService


@dataclass
class RagSearchResult:
    product: Product
    score: float
    matched_chunk_types: list[str]
    matched_snippets: list[str]


class RagService:
    def __init__(
        self,
        product_service: ProductService | None = None,
        embedder: Embedder | None = None,
        vector_store: VectorStore | None = None,
    ):
        self.product_service = product_service or ProductService()
        self.chunker = ProductChunker()
        self.embedder = embedder or Embedder()
        self.vector_store = vector_store or VectorStore()
        self.retriever = Retriever(embedder=self.embedder, vector_store=self.vector_store)
        self.reranker = Reranker()

    async def rebuild_index(self) -> int:
        self.vector_store.reset()
        products = self.product_service.products
        chunks = self.chunker.chunk_products(products)
        embeddings = await self.embedder.embed_many([chunk.text for chunk in chunks])
        self.vector_store.add_chunks(chunks, embeddings)
        return len(chunks)

    async def search(
        self,
        query: str,
        category: str | None = None,
        brand: str | None = None,
        price_min: float | None = None,
        price_max: float | None = None,
        exclude_keywords: list[str] | None = None,
        top_k: int | None = None,
    ) -> list[RagSearchResult]:
        chunks = await self.retriever.retrieve(query, category=category, brand=brand, top_k=top_k)
        chunks = self.reranker.rerank(chunks, query=query, exclude_keywords=exclude_keywords)
        if not chunks:
            chunks = await self._fallback_candidates(
                query=query,
                category=category,
                brand=brand,
                price_min=price_min,
                price_max=price_max,
                exclude_keywords=exclude_keywords,
            )

        results: list[RagSearchResult] = []
        for chunk in chunks:
            product = self.product_service.get_product(chunk.product_id)
            if not self._passes_hard_constraints(query, product):
                continue
            if price_min is not None and product.base_price < price_min:
                continue
            if price_max is not None and product.base_price > price_max:
                continue
            results.append(
                RagSearchResult(
                    product=product,
                    score=chunk.score,
                    matched_chunk_types=[chunk.chunk_type],
                    matched_snippets=[chunk.text],
                )
            )
            if len(results) >= (top_k or settings.rag_top_k):
                break
        return results

    @staticmethod
    def _passes_hard_constraints(query: str, product: Product) -> bool:
        query_text = query.lower()
        for keyword, rule in DOMAIN_RULES.items():
            if keyword not in query_text:
                continue
            constraint_fields = rule.get("hard_constraint_fields", [])
            constraint_match = rule.get("hard_constraint_match", [keyword])
            if not constraint_fields:
                continue
            for field_name in constraint_fields:
                field_value = getattr(product, field_name, "").lower()
                if any(match in field_value for match in constraint_match):
                    return True
            return False
        return True

    async def _fallback_candidates(
        self,
        query: str,
        category: str | None,
        brand: str | None,
        price_min: float | None,
        price_max: float | None,
        exclude_keywords: list[str] | None,
    ) -> list:
        products = self.product_service.products
        excluded = [keyword.lower() for keyword in (exclude_keywords or []) if keyword]
        query_terms = self._extract_terms(query)
        query_text = query.lower()
        candidates = []
        for product in products:
            if category and product.category != category:
                continue
            if brand and product.brand != brand:
                continue
            if price_min is not None and product.base_price < price_min:
                continue
            if price_max is not None and product.base_price > price_max:
                continue
            text = " ".join(
                [
                    product.title,
                    product.brand,
                    product.category,
                    product.sub_category,
                    product.rag_knowledge.get("marketing_description", ""),
                    " ".join((item.get("question", "") + item.get("answer", "")) for item in product.rag_knowledge.get("official_faq", [])),
                    " ".join(review.get("content", "") for review in product.rag_knowledge.get("user_reviews", [])),
                ]
            ).lower()
            if excluded and any(keyword in text for keyword in excluded):
                continue
            score = 0
            for term in query_terms:
                if term and term in text:
                    score += 1
            for keyword, rule in DOMAIN_RULES.items():
                if keyword not in query_text:
                    continue
                boost_terms = rule.get("boost_terms", [])
                if boost_terms and any(term in text for term in boost_terms):
                    score += 2
                sub_categories = rule.get("sub_categories", [])
                if sub_categories and product.sub_category in sub_categories:
                    score += 3
            if score > 0 or not query_terms:
                candidates.append((score, product))
        candidates.sort(key=lambda item: (item[0], item[1].base_price), reverse=True)
        return [
            type(
                "FallbackChunk",
                (),
                {
                    "product_id": product.product_id,
                    "chunk_type": "fallback",
                    "score": score / max(len(query_terms), 1) if query_terms else 0.1,
                    "text": product.title,
                },
            )()
            for score, product in candidates[: (settings.rag_top_k * 2)]
        ]

    @staticmethod
    def _extract_terms(query: str) -> list[str]:
        raw_terms = re.split(r"[^\w\u4e00-\u9fff]+", query.lower())
        terms = [term for term in raw_terms if len(term) >= 2]
        if query:
            terms.extend([query.lower().replace(" ", "")])
        for keyword, rule in DOMAIN_RULES.items():
            if keyword in query:
                terms.extend([keyword] + rule.get("boost_terms", []))
        return list(dict.fromkeys(terms))
