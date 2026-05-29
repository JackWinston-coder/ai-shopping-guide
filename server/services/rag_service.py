from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import asyncio
from dataclasses import dataclass
from pathlib import Path

import jieba

from server.config import settings
from server.models.product import Product
from server.rag.chunker import ProductChunker
from server.rag.embedder import Embedder
from server.rag.query_profile import build_query_profile
from server.rag.reranker import Reranker
from server.rag.retriever import Retriever
from server.rag.vector_store import VectorStore
from server.services.product_service import ProductService

logger = logging.getLogger(__name__)


@dataclass
class RagSearchResult:
    product: Product
    score: float
    matched_chunk_types: list[str]
    matched_snippets: list[str]


@dataclass
class FallbackChunk:
    product_id: str
    chunk_type: str = "fallback"
    score: float = 0.0
    text: str = ""


class EmbeddingCache:
    def __init__(self, cache_dir: str | None = None) -> None:
        cache_path = Path(cache_dir or os.path.join(os.path.dirname(__file__), "..", ".cache"))
        cache_path.mkdir(parents=True, exist_ok=True)
        self._db_path = str(cache_path / "embedding_cache.db")
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS embeddings (
                    text_hash TEXT PRIMARY KEY,
                    embedding BLOB NOT NULL,
                    model_name TEXT NOT NULL,
                    created_at REAL DEFAULT (strftime('%s','now'))
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_text_hash ON embeddings(text_hash)")

    @staticmethod
    def _hash_text(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    async def get(self, text: str, model_name: str) -> list[float] | None:
        return await asyncio.to_thread(self._sync_get, text, model_name)

    def _sync_get(self, text: str, model_name: str) -> list[float] | None:
        text_hash = self._hash_text(text)
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT embedding FROM embeddings WHERE text_hash = ? AND model_name = ?",
                (text_hash, model_name),
            ).fetchone()
            if row is None:
                return None
            return json.loads(row[0])

    async def put(self, text: str, model_name: str, embedding: list[float]) -> None:
        await asyncio.to_thread(self._sync_put, text, model_name, embedding)

    def _sync_put(self, text: str, model_name: str, embedding: list[float]) -> None:
        text_hash = self._hash_text(text)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO embeddings (text_hash, embedding, model_name) VALUES (?, ?, ?)",
                (text_hash, json.dumps(embedding), model_name),
            )

    async def get_many(self, texts: list[str], model_name: str) -> tuple[list[list[float] | None], list[int]]:
        results: list[list[float] | None] = []
        miss_indices: list[int] = []
        for i, text in enumerate(texts):
            cached = await self.get(text, model_name)
            results.append(cached)
            if cached is None:
                miss_indices.append(i)
        return results, miss_indices

    async def put_many(self, texts: list[str], model_name: str, embeddings: list[list[float]]) -> None:
        await asyncio.to_thread(self._sync_put_many, texts, model_name, embeddings)

    def _sync_put_many(self, texts: list[str], model_name: str, embeddings: list[list[float]]) -> None:
        with sqlite3.connect(self._db_path) as conn:
            rows = []
            for text, emb in zip(texts, embeddings):
                text_hash = self._hash_text(text)
                rows.append((text_hash, json.dumps(emb), model_name))
            conn.executemany(
                "INSERT OR REPLACE INTO embeddings (text_hash, embedding, model_name) VALUES (?, ?, ?)",
                rows,
            )


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
        self._embedding_cache = EmbeddingCache()
        self._hyde_enabled = True

    async def rebuild_index(self) -> int:
        self.vector_store.reset()
        products = self.product_service.products
        chunks = self.chunker.chunk_products(products)

        texts = [chunk.text for chunk in chunks]
        model_name = self.embedder.model_name

        cached_results, miss_indices = await self._embedding_cache.get_many(texts, model_name)

        if miss_indices:
            miss_texts = [texts[i] for i in miss_indices]
            new_embeddings = await self.embedder.embed_many(miss_texts)
            await self._embedding_cache.put_many(miss_texts, model_name, new_embeddings)
            for idx, emb in zip(miss_indices, new_embeddings):
                cached_results[idx] = emb

        embeddings = cached_results
        self.vector_store.add_chunks(chunks, embeddings)

        for chunk in chunks:
            self.retriever.register_chunk(
                chunk.id,
                chunk.text,
                {
                    "product_id": chunk.product_id,
                    "chunk_type": chunk.chunk_type,
                    "category": chunk.metadata.get("category", ""),
                    "brand": chunk.metadata.get("brand", ""),
                },
            )
        self.retriever.build_bm25_index()

        logger.info("RAG index rebuilt: %d chunks, %d cache hits, %d cache misses",
                     len(chunks), len(chunks) - len(miss_indices), len(miss_indices))
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
        profile = build_query_profile(query)
        effective_category = category or profile.category_hint
        effective_exclude = self._merge_exclude_keywords(exclude_keywords, profile.exclude_terms)

        enhanced_query = await self._enhance_query(query)

        chunks = await self.retriever.retrieve(enhanced_query, category=effective_category, brand=brand, top_k=top_k)
        chunks = self.reranker.rerank(
            chunks,
            query=query,
            exclude_keywords=effective_exclude,
            boost_terms=profile.boost_terms,
            hard_terms=profile.hard_terms,
        )

        if not chunks:
            chunks = await self._fallback_candidates(
                query=query,
                category=effective_category,
                brand=brand,
                price_min=price_min,
                price_max=price_max,
                exclude_keywords=effective_exclude,
                profile=profile,
            )

        results: list[RagSearchResult] = []
        for chunk in chunks:
            product = self.product_service.get_product(chunk.product_id)
            if not product:
                continue
            if not self._passes_hard_constraints(profile, product):
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

    async def _enhance_query(self, query: str) -> str:
        if not self._hyde_enabled:
            return query
        try:
            client = self.embedder.client
            if not client.api_key:
                return query
            response = await client.chat(
                messages=[
                    {"role": "system", "content": "你是一个电商导购助手。请根据用户的问题，生成一段简短的商品描述（50字以内），描述最可能满足用户需求的商品特征。只输出描述，不要解释。"},
                    {"role": "user", "content": query},
                ],
                temperature=0.3,
                max_tokens=80,
            )
            if response and hasattr(response, "choices") and response.choices:
                content = response.choices[0].message.content
                if content and len(content.strip()) > 5:
                    logger.debug("HyDE: query='%s' → hyde='%s'", query, content.strip())
                    return f"{query} {content.strip()}"
        except Exception as e:
            logger.debug("HyDE enhancement skipped: %s", e)
        return query

    @staticmethod
    def _passes_hard_constraints(profile, product: Product) -> bool:
        if not profile.hard_terms:
            return True
        text = " ".join(
            [
                product.title,
                product.brand,
                product.category,
                product.sub_category,
                product.rag_knowledge.get("marketing_description", ""),
            ]
        ).lower()
        return any(term.lower() in text for term in profile.hard_terms)

    async def _fallback_candidates(
        self,
        query: str,
        category: str | None,
        brand: str | None,
        price_min: float | None,
        price_max: float | None,
        exclude_keywords: list[str] | None,
        profile,
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
            for term in profile.boost_terms:
                if term in text:
                    score += 2
            for sub_category in profile.sub_category_hints:
                if product.sub_category == sub_category:
                    score += 3
            if profile.category_hint and product.category == profile.category_hint:
                score += 1
            if score > 0 or not query_terms:
                candidates.append((score, product))
        candidates.sort(key=lambda item: (item[0], item[1].base_price), reverse=True)
        return [
            FallbackChunk(
                product_id=product.product_id,
                score=score / max(len(query_terms), 1) if query_terms else 0.1,
                text=product.title,
            )
            for score, product in candidates[: (settings.rag_top_k * 2)]
        ]

    @staticmethod
    def _extract_terms(query: str) -> list[str]:
        words = [w for w in jieba.cut(query) if w.strip() and len(w) >= 2]
        seen: dict[str, None] = {}
        unique: list[str] = []
        for w in words:
            if w not in seen:
                seen[w] = None
                unique.append(w)
        return unique

    @staticmethod
    def _merge_exclude_keywords(*groups: list[str] | None) -> list[str]:
        merged: list[str] = []
        for group in groups:
            for keyword in group or []:
                if keyword and keyword not in merged:
                    merged.append(keyword)
        return merged
