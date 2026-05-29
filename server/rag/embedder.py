from server.llm.zhipu_client import ZhipuClient


class Embedder:
    def __init__(self, client: ZhipuClient | None = None, batch_size: int = 64):
        self.client = client or ZhipuClient()
        self.batch_size = batch_size

    @property
    def model_name(self) -> str:
        return self.client.embedding_model

    async def embed(self, text: str) -> list[float]:
        return (await self.client.embed([text]))[0]

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for index in range(0, len(texts), self.batch_size):
            embeddings.extend(await self.client.embed(texts[index : index + self.batch_size]))
        return embeddings
