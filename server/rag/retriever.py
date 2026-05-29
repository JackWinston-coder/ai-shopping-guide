from __future__ import annotations

import logging
from dataclasses import dataclass

from server.config import settings
from server.rag.bm25_retriever import BM25Retriever, reciprocal_rank_fusion
from server.rag.embedder import Embedder
from server.rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    chunk_id: str
    product_id: str
    chunk_type: str
    text: str
    score: float
    metadata: dict


class Retriever:
    def __init__(self, embedder: Embedder | None = None, vector_store: VectorStore | None = None):
        self.embedder = embedder or Embedder()
        self.vector_store = vector_store or VectorStore()
        self.bm25 = BM25Retriever()
        self._chunk_text_map: dict[str, str] = {}
        self._chunk_meta_map: dict[str, dict] = {}

    def build_bm25_index(self) -> None:
        chunk_ids: list[str] = []
        texts: list[str] = []
        metadatas: list[dict] = []
        for cid, text in self._chunk_text_map.items():
            chunk_ids.append(cid)
            texts.append(text)
            metadatas.append(self._chunk_meta_map.get(cid, {}))
        if chunk_ids:
            self.bm25.index(chunk_ids, texts, metadatas)

    def register_chunk(self, chunk_id: str, text: str, metadata: dict) -> None:
        self._chunk_text_map[chunk_id] = text
        self._chunk_meta_map[chunk_id] = metadata

    async def retrieve(
        self,
        query: str,
        category: str | None = None,
        brand: str | None = None,
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        k = top_k or settings.rag_top_k
        n_candidates = k * settings.rag_candidate_multiplier

        embedding = await self.embedder.embed(query)
        dense_results = self.vector_store.query(
            embedding=embedding,
            n_results=n_candidates,
            where=self._build_where(category=category, brand=brand),
        )
        dense_chunks = self._parse_results(dense_results)

        sparse_results = self.bm25.search(query, top_k=n_candidates)

        if sparse_results and dense_chunks:
            return self._rrf_merge(dense_chunks, sparse_results, k)

        if dense_chunks:
            return dense_chunks[:k]

        if sparse_results:
            return self._sparse_to_chunks(sparse_results)[:k]

        return []

    def _rrf_merge(
        self,
        dense_chunks: list[RetrievedChunk],
        sparse_results: list,
        top_k: int,
    ) -> list[RetrievedChunk]:
        dense_ranked = [(c.chunk_id, c.score) for c in dense_chunks]
        sparse_ranked = [(r.chunk_id, r.score) for r in sparse_results]
        fused = reciprocal_rank_fusion(dense_ranked, sparse_ranked, k=60)

        chunk_map: dict[str, RetrievedChunk] = {c.chunk_id: c for c in dense_chunks}
        for r in sparse_results:
            if r.chunk_id not in chunk_map:
                chunk_map[r.chunk_id] = RetrievedChunk(
                    chunk_id=r.chunk_id,
                    product_id=r.metadata.get("product_id", ""),
                    chunk_type=r.metadata.get("chunk_type", ""),
                    text=r.text,
                    score=r.score,
                    metadata=r.metadata,
                )

        results: list[RetrievedChunk] = []
        for chunk_id, rrf_score in fused[:top_k]:
            chunk = chunk_map[chunk_id]
            results.append(
                RetrievedChunk(
                    chunk_id=chunk.chunk_id,
                    product_id=chunk.product_id,
                    chunk_type=chunk.chunk_type,
                    text=chunk.text,
                    score=rrf_score,
                    metadata=chunk.metadata,
                )
            )
        return results

    @staticmethod
    def _sparse_to_chunks(sparse_results: list) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                chunk_id=r.chunk_id,
                product_id=r.metadata.get("product_id", ""),
                chunk_type=r.metadata.get("chunk_type", ""),
                text=r.text,
                score=r.score,
                metadata=r.metadata,
            )
            for r in sparse_results
        ]

    @staticmethod
    def _build_where(category: str | None = None, brand: str | None = None) -> dict | None:
        clauses = []
        if category:
            clauses.append({"category": category})
        if brand:
            clauses.append({"brand": brand})
        if not clauses:
            return None
        if len(clauses) == 1:
            return clauses[0]
        return {"$and": clauses}

    @staticmethod
    def _parse_results(results: dict) -> list[RetrievedChunk]:
        chunks: list[RetrievedChunk] = []
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        for chunk_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    product_id=metadata["product_id"],
                    chunk_type=metadata["chunk_type"],
                    text=document,
                    score=max(0.0, 1.0 - float(distance)),
                    metadata=metadata,
                )
            )
        return chunks
