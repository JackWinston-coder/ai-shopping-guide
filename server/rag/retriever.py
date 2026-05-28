from dataclasses import dataclass

from server.config import settings
from server.rag.embedder import Embedder
from server.rag.vector_store import VectorStore


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

    async def retrieve(
        self,
        query: str,
        category: str | None = None,
        brand: str | None = None,
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        embedding = await self.embedder.embed(query)
        n_results = (top_k or settings.rag_top_k) * settings.rag_candidate_multiplier
        results = self.vector_store.query(
            embedding=embedding,
            n_results=n_results,
            where=self._build_where(category=category, brand=brand),
        )
        return self._parse_results(results)

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

