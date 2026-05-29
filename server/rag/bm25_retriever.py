from __future__ import annotations

import logging
from dataclasses import dataclass, field

import jieba

from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


@dataclass
class BM25Result:
    chunk_id: str
    score: float
    text: str
    metadata: dict = field(default_factory=dict)


def _tokenize(text: str) -> list[str]:
    return [w for w in jieba.cut(text) if w.strip()]


class BM25Retriever:
    def __init__(self) -> None:
        self._bm25: BM25Okapi | None = None
        self._chunk_ids: list[str] = []
        self._texts: list[str] = []
        self._metadatas: list[dict] = []
        self._tokenized_corpus: list[list[str]] = []

    def index(
        self,
        chunk_ids: list[str],
        texts: list[str],
        metadatas: list[dict] | None = None,
    ) -> None:
        self._chunk_ids = chunk_ids
        self._texts = texts
        self._metadatas = metadatas or [{} for _ in chunk_ids]
        self._tokenized_corpus = [_tokenize(t) for t in texts]
        self._bm25 = BM25Okapi(self._tokenized_corpus)
        logger.info("BM25 index built with %d documents", len(chunk_ids))

    def search(self, query: str, top_k: int = 10) -> list[BM25Result]:
        if self._bm25 is None or not self._chunk_ids:
            return []
        tokenized_query = _tokenize(query)
        scores = self._bm25.get_scores(tokenized_query)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        results: list[BM25Result] = []
        for idx, score in ranked[:top_k]:
            if score <= 0:
                continue
            results.append(
                BM25Result(
                    chunk_id=self._chunk_ids[idx],
                    score=float(score),
                    text=self._texts[idx],
                    metadata=self._metadatas[idx],
                )
            )
        return results

    @property
    def doc_count(self) -> int:
        return len(self._chunk_ids)


def reciprocal_rank_fusion(
    dense_results: list[tuple[str, float]],
    sparse_results: list[tuple[str, float]],
    k: int = 60,
) -> list[tuple[str, float]]:
    rrf_scores: dict[str, float] = {}
    for rank, (chunk_id, _score) in enumerate(dense_results, start=1):
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    for rank, (chunk_id, _score) in enumerate(sparse_results, start=1):
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return ranked
