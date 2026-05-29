from pathlib import Path

import chromadb

from server.config import settings
from server.rag.chunker import ProductChunk

COLLECTION_NAME = "product_knowledge"


class VectorStore:
    def __init__(self, persist_path: str | None = None):
        self.persist_path = Path(persist_path or settings.chroma_path)
        self.persist_path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.persist_path))
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def reset(self) -> None:
        try:
            self.client.delete_collection(COLLECTION_NAME)
        except Exception as exc:
            if "does not exist" not in str(exc).lower():
                raise
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(self, chunks: list[ProductChunk], embeddings: list[list[float]]) -> None:
        if not chunks:
            return
        self.collection.upsert(
            ids=[chunk.id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            embeddings=embeddings,
            metadatas=[chunk.metadata for chunk in chunks],
        )

    def query(self, embedding: list[float], n_results: int, where: dict | None = None) -> dict:
        kwargs = {
            "query_embeddings": [embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where
        return self.collection.query(**kwargs)

    def count(self) -> int:
        return self.collection.count()
