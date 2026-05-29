from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

import jieba

from server.rag.retriever import RetrievedChunk

if TYPE_CHECKING:
    from server.llm.zhipu_client import ZhipuClient

logger = logging.getLogger(__name__)


class Reranker:
    def __init__(self, use_llm: bool = False, llm_client: ZhipuClient | None = None) -> None:
        self._use_llm = use_llm
        self._llm_client = llm_client

    def rerank(
        self,
        chunks: list[RetrievedChunk],
        query: str,
        exclude_keywords: list[str] | None = None,
        boost_terms: list[str] | None = None,
        hard_terms: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        exclude_keywords = [keyword for keyword in (exclude_keywords or []) if keyword]
        if exclude_keywords:
            chunks = [
                chunk
                for chunk in chunks
                if not any(keyword.lower() in chunk.text.lower() for keyword in exclude_keywords)
            ]

        if not chunks:
            return []

        query_words = set(jieba.cut(query))
        query_words = {w for w in query_words if w.strip()}
        boost_terms = [term for term in (boost_terms or []) if term]
        hard_terms = [term for term in (hard_terms or []) if term]

        best_by_product: dict[str, RetrievedChunk] = {}
        type_bonus = defaultdict(float, {
            "marketing": 0.05,
            "faq": 0.03,
            "review_positive": 0.02,
            "review_negative": 0.01,
            "spec": 0.04,
            "sku": 0.04,
        })

        for chunk in chunks:
            text_words = set(jieba.cut(chunk.text))
            text_words = {w for w in text_words if w.strip()}

            overlap = query_words & text_words
            lexical = len(overlap) / max(len(query_words), 1)

            boost_score = sum(0.06 for term in boost_terms if term.lower() in chunk.text.lower())
            hard_score = sum(0.1 for term in hard_terms if term.lower() in chunk.text.lower())

            final_score = chunk.score * 0.68 + lexical * 0.16 + boost_score + hard_score + type_bonus[chunk.chunk_type]

            enriched = RetrievedChunk(
                chunk_id=chunk.chunk_id,
                product_id=chunk.product_id,
                chunk_type=chunk.chunk_type,
                text=chunk.text,
                score=final_score,
                metadata=chunk.metadata,
            )
            current = best_by_product.get(chunk.product_id)
            if current is None or enriched.score > current.score:
                best_by_product[chunk.product_id] = enriched

        scored_chunks = sorted(best_by_product.values(), key=lambda item: item.score, reverse=True)

        if self._use_llm and scored_chunks:
            scored_chunks = self._llm_rerank(query, scored_chunks)

        return scored_chunks

    def _llm_rerank(self, query: str, chunks: list[RetrievedChunk], top_n: int = 8) -> list[RetrievedChunk]:
        candidates = chunks[:top_n]
        try:
            from server.llm.zhipu_client import ZhipuClient
            client = self._llm_client or ZhipuClient()
            if not client.api_key:
                return chunks

            doc_list = "\n".join(
                f"[{i}] {c.product_id} | {c.chunk_type} | {c.text[:120]}"
                for i, c in enumerate(candidates)
            )
            prompt = (
                f"用户查询：{query}\n\n"
                f"候选商品片段：\n{doc_list}\n\n"
                f"请按与查询的相关性从高到低排列，只输出编号用逗号分隔，例如：3,1,0,2\n"
                f"输出："
            )
            response = client.chat_sync(
                messages=[
                    {"role": "system", "content": "你是电商搜索相关性评估专家。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=50,
            )
            if response:
                order = [int(x.strip()) for x in response.strip().split(",") if x.strip().isdigit()]
                reordered: list[RetrievedChunk] = []
                seen: set[int] = set()
                for idx in order:
                    if 0 <= idx < len(candidates) and idx not in seen:
                        reordered.append(candidates[idx])
                        seen.add(idx)
                for i, c in enumerate(candidates):
                    if i not in seen:
                        reordered.append(c)
                return reordered + chunks[top_n:]
        except Exception as e:
            logger.debug("LLM rerank skipped: %s", e)
        return chunks
