import json
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any, Callable, Awaitable

from server.config import settings
from server.models.chat import SSEEvent, SSEEventType
from server.agents.context import ConversationContext

logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, dict] = {}
        self._handlers: dict[str, Callable[..., Awaitable[Any]]] = {}

    def register(
        self,
        name: str,
        schema: dict,
        handler: Callable[..., Awaitable[Any]],
    ):
        self._tools[name] = schema
        self._handlers[name] = handler

    def get_schemas(self) -> list[dict]:
        return list(self._tools.values())

    async def execute(self, name: str, arguments: dict, context: ConversationContext | None = None) -> Any:
        handler = self._handlers.get(name)
        if handler is None:
            raise ValueError(f"Tool not found: {name}")
        return await handler(**arguments, context=context)


class BaseAgent(ABC):
    agent_name: str = "base"
    llm_model: str = ""
    llm_temperature: float = 0.1
    llm_max_tokens: int = 1024

    def __init__(self, llm_client, tool_registry: ToolRegistry | None = None):
        self.llm_client = llm_client
        self.tool_registry = tool_registry

    @abstractmethod
    def _build_messages(self, user_message: str, context: ConversationContext) -> list[dict]:
        ...

    async def run(self, user_message: str, context: ConversationContext) -> AsyncGenerator[SSEEvent, None]:
        messages = self._build_messages(user_message, context)
        model = self.llm_model or settings.zhipu_llm_model_fast

        while True:
            try:
                response = await self.llm_client.chat(
                    messages=messages,
                    tools=self.tool_registry.get_schemas() if self.tool_registry else [],
                    model=model,
                    temperature=self.llm_temperature,
                    max_tokens=self.llm_max_tokens,
                )
            except Exception as exc:
                logger.error("%s LLM call failed: %s", self.agent_name, exc)
                yield SSEEvent(type=SSEEventType.ERROR, data={"code": "LLM_ERROR", "message": str(exc)})
                break

            choice = response.choices[0]
            assistant_message = choice.message

            if assistant_message.content:
                yield SSEEvent(type=SSEEventType.TEXT_DELTA, data={"content": assistant_message.content})

            if not assistant_message.tool_calls:
                break

            messages.append({
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [tc.model_dump() for tc in assistant_message.tool_calls],
            })

            for tool_call in assistant_message.tool_calls:
                func = tool_call.function
                name = func.name
                try:
                    arguments = json.loads(func.arguments) if isinstance(func.arguments, str) else func.arguments
                except json.JSONDecodeError:
                    arguments = {}

                tool_result = await self._execute_tool(name, arguments, context)

                yield SSEEvent(type=SSEEventType.TOOL_RESULT, data={"tool": name, "result": tool_result})

                async for extra_event in self._on_tool_result(name, tool_result, context):
                    yield extra_event

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result, ensure_ascii=False),
                })

    async def _execute_tool(self, name: str, arguments: dict, context: ConversationContext) -> dict:
        try:
            result = await self.tool_registry.execute(name, arguments, context=context)
            return result if isinstance(result, dict) else {"success": True, "data": result}
        except Exception as exc:
            logger.warning("Tool %s execution error: %s", name, exc)
            return {"success": False, "error": str(exc)}

    async def _on_tool_result(self, name: str, result: dict, context: ConversationContext) -> AsyncGenerator[SSEEvent, None]:
        return
        yield
