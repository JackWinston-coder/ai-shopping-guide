import asyncio
import hashlib
import math
from datetime import datetime
from typing import Any, AsyncIterator

from pydantic import BaseModel

from server.config import DOMAIN_RULES, settings


class APICallRecord(BaseModel):
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    call_type: str
    timestamp: datetime


MAX_CALL_RECORDS = 1000

_DOMAIN_KEYWORD_INDICES: dict[str, int] = {}
_next_index = 0
for _kw in DOMAIN_RULES:
    _DOMAIN_KEYWORD_INDICES[_kw] = _next_index
    _next_index += 1


class ZhipuClient:
    def __init__(
        self,
        api_key: str | None = None,
        llm_model: str | None = None,
        embedding_model: str | None = None,
    ):
        self.api_key = api_key if api_key is not None else settings.zhipu_api_key
        self.llm_model = llm_model or settings.zhipu_llm_model
        self.embedding_model = embedding_model or settings.zhipu_embedding_model
        self._call_records: list[APICallRecord] = []
        self._client = None
        if self.api_key:
            from zhipuai import ZhipuAI

            self._client = ZhipuAI(api_key=self.api_key)

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> Any:
        if self._client is None:
            raise RuntimeError("ZHIPU_API_KEY is required for LLM chat")
        response = await asyncio.to_thread(
            self._client.chat.completions.create,
            model=model or self.llm_model,
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        usage = getattr(response, "usage", None)
        self._record_call(
            APICallRecord(
                model=model or self.llm_model,
                prompt_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
                completion_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
                total_tokens=getattr(usage, "total_tokens", 0) if usage else 0,
                call_type="chat",
                timestamp=datetime.now(),
            )
        )
        return response

    async def chat_stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[Any]:
        if self._client is None:
            raise RuntimeError("ZHIPU_API_KEY is required for LLM chat_stream")
        stream = await asyncio.to_thread(
            self._client.chat.completions.create,
            model=model or self.llm_model,
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in stream:
            yield chunk
        self._record_call(
            APICallRecord(
                model=model or self.llm_model,
                call_type="chat",
                timestamp=datetime.now(),
            )
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if self._client is None:
            embeddings = [self._local_embed(text) for text in texts]
            self._record_call(
                APICallRecord(
                    model="local-hashing-embedding",
                    total_tokens=sum(len(text) for text in texts),
                    call_type="embedding",
                    timestamp=datetime.now(),
                )
            )
            return embeddings

        response = await asyncio.to_thread(
            self._client.embeddings.create,
            model=self.embedding_model,
            input=texts,
        )
        embeddings = [item.embedding for item in response.data]
        usage = getattr(response, "usage", None)
        self._record_call(
            APICallRecord(
                model=self.embedding_model,
                prompt_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
                total_tokens=getattr(usage, "total_tokens", 0) if usage else 0,
                call_type="embedding",
                timestamp=datetime.now(),
            )
        )
        return embeddings

    async def image_understand(self, image_url: str, prompt: str) -> str:
        if self._client is None:
            raise RuntimeError("ZHIPU_API_KEY is required for image understanding")
        response = await asyncio.to_thread(
            self._client.chat.completions.create,
            model=self.llm_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
        )
        self._record_call(
            APICallRecord(model=self.llm_model, call_type="image_understand", timestamp=datetime.now())
        )
        return response.choices[0].message.content

    def get_call_stats(self) -> dict:
        by_model: dict[str, dict[str, int]] = {}
        by_type: dict[str, dict[str, int]] = {}
        for record in self._call_records:
            by_model.setdefault(record.model, {"calls": 0, "tokens": 0})
            by_model[record.model]["calls"] += 1
            by_model[record.model]["tokens"] += record.total_tokens
            by_type.setdefault(record.call_type, {"calls": 0, "tokens": 0})
            by_type[record.call_type]["calls"] += 1
            by_type[record.call_type]["tokens"] += record.total_tokens
        return {
            "total_calls": len(self._call_records),
            "total_tokens": sum(record.total_tokens for record in self._call_records),
            "by_model": by_model,
            "by_type": by_type,
        }

    def reset_stats(self) -> None:
        self._call_records.clear()

    def _record_call(self, record: APICallRecord) -> None:
        self._call_records.append(record)
        if len(self._call_records) > MAX_CALL_RECORDS:
            self._call_records = self._call_records[-MAX_CALL_RECORDS:]

    def _local_embed(self, text: str) -> list[float]:
        dimensions = settings.local_embedding_dimensions
        vector = [0.0] * dimensions
        normalized = "".join(text.lower().split())
        tokens = self._tokenize_for_local_embedding(normalized)
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        for char in normalized:
            if char.strip():
                digest = hashlib.sha256(f"c:{char}".encode("utf-8")).digest()
                index = int.from_bytes(digest[:4], "big") % dimensions
                vector[index] += 0.8
        for index in range(max(len(normalized) - 1, 0)):
            bigram = normalized[index : index + 2]
            digest = hashlib.sha256(f"b:{bigram}".encode("utf-8")).digest()
            vector[int.from_bytes(digest[:4], "big") % dimensions] += 0.6
        for keyword, vec_index in _DOMAIN_KEYWORD_INDICES.items():
            if keyword in text and vec_index < dimensions:
                vector[vec_index] += 1.5
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    @staticmethod
    def _tokenize_for_local_embedding(text: str) -> list[str]:
        tokens: list[str] = []
        tokens.extend(char for char in text if not char.isspace())
        tokens.extend(text[index : index + 2] for index in range(max(len(text) - 1, 0)))
        tokens.extend(text[index : index + 3] for index in range(max(len(text) - 2, 0)))
        return tokens or [text]
