from collections import defaultdict

from server.rag.retriever import RetrievedChunk


class Reranker:
    def rerank(self, chunks: list[RetrievedChunk], query: str, exclude_keywords: list[str] | None = None) -> list[RetrievedChunk]:
        exclude_keywords = [keyword for keyword in (exclude_keywords or []) if keyword]
        if exclude_keywords:
            chunks = [
                chunk
                for chunk in chunks
                if not any(keyword.lower() in chunk.text.lower() for keyword in exclude_keywords)
            ]

        query_terms = {char for char in query.lower() if not char.isspace()}
        best_by_product: dict[str, RetrievedChunk] = {}
        type_bonus = defaultdict(float, {"marketing": 0.05, "faq": 0.03, "review_positive": 0.02, "review_negative": 0.01})
        for chunk in chunks:
            text_terms = {char for char in chunk.text.lower() if not char.isspace()}
            lexical = len(query_terms & text_terms) / max(len(query_terms), 1)
            final_score = chunk.score * 0.75 + lexical * 0.2 + type_bonus[chunk.chunk_type]
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
        return sorted(best_by_product.values(), key=lambda item: item.score, reverse=True)
