import json
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any, Callable, Awaitable

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

    def __init__(self, llm_client, tool_registry: ToolRegistry | None = None):
        self.llm_client = llm_client
        self.tool_registry = tool_registry

    @abstractmethod
    async def run(self, user_message: str, context: ConversationContext) -> AsyncGenerator[SSEEvent, None]:
        yield  # pragma: no cover

    def _build_tool_messages(
        self,
        messages: list[dict],
        tool_calls: list[dict],
    ) -> list[dict]:
        result_messages = []
        for tool_call in tool_calls:
            func = tool_call.get("function", {})
            name = func.get("name", "")
            arguments_str = func.get("arguments", "{}")
            try:
                arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str
            except json.JSONDecodeError:
                arguments = {}
            tool_call_id = tool_call.get("id", name)
            result_messages.append({"role": "assistant", "content": None, "tool_calls": [tool_call]})
            tool_result = {"success": False, "error": f"Tool {name} not found"}
            if self.tool_registry and name in self.tool_registry._handlers:
                try:
                    tool_result = self.tool_registry.execute(name, arguments)
                except Exception as exc:
                    tool_result = {"success": False, "error": str(exc)}
                    logger.warning("Tool %s execution error: %s", name, exc)
            result_messages.append({"role": "tool", "tool_call_id": tool_call_id, "content": json.dumps(tool_result, ensure_ascii=False)})
        return result_messages
