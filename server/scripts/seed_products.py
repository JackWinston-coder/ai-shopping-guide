from server.rag.chunker import ProductChunker
from server.rag.embedder import Embedder
from server.rag.vector_store import VectorStore
from server.services.product_service import ProductService


async def main() -> None:
    service = ProductService()
    chunker = ProductChunker()
    embedder = Embedder()
    vector_store = VectorStore()
    vector_store.reset()
    chunks = chunker.chunk_products(service.products)
    embeddings = await embedder.embed_many([chunk.text for chunk in chunks])
    vector_store.add_chunks(chunks, embeddings)
    print(f"seeded {len(chunks)} chunks into Chroma")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
