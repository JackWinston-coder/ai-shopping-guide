import logging

from server.config import settings
from server.llm.zhipu_client import ZhipuClient
from server.services.session_service import SessionService

logger = logging.getLogger(__name__)

SUMMARY_PROMPT = """你是一个对话摘要生成器。请将以下用户与AI导购助手的对话历史压缩为一段简洁的摘要。

## 要求

1. 保留用户的核心需求（想买什么、预算、偏好、排除条件）
2. 保留已推荐的商品名称和ID（如果用户表达了偏好，也保留）
3. 保留购物车操作结果（加了什么、删了什么）
4. 保留订单状态（是否已下单）
5. 丢弃闲聊、重复提问、无效信息
6. 摘要不超过 200 字
7. 使用第三人称客观描述

## 输出格式

直接输出摘要文本，不要输出任何前缀或标签。

## 对话历史

{conversation_text}"""


class SummaryService:
    def __init__(self, llm_client: ZhipuClient, context_window: int | None = None):
        self.llm_client = llm_client
        self.context_window = context_window or settings.session_context_window

    async def generate_if_needed(
        self,
        session_id: str,
        session_service: SessionService,
    ) -> str | None:
        cursor = await session_service.db.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        )
        rows = await cursor.fetchall()
        messages = list(rows)

        if len(messages) <= self.context_window:
            return None

        session = await session_service.get_session_by_id(session_id)
        old_messages = messages[: -self.context_window]

        if session and session.summary_text and len(messages) <= self.context_window + 2:
            return session.summary_text

        conversation_text = self._format_messages(old_messages)
        if not conversation_text.strip():
            return None

        try:
            response = await self.llm_client.chat(
                messages=[
                    {"role": "system", "content": SUMMARY_PROMPT.format(conversation_text=conversation_text)},
                    {"role": "user", "content": "请生成摘要"},
                ],
                model=settings.zhipu_llm_model_fast,
                temperature=0.1,
                max_tokens=settings.summary_max_tokens,
            )
            return response.choices[0].message.content
        except Exception as exc:
            logger.warning("Summary generation failed: %s", exc)
            return None

    @staticmethod
    def _format_messages(messages: list) -> str:
        lines = []
        for msg in messages:
            role = msg["role"] if isinstance(msg, dict) else msg.role
            content = msg["content"] if isinstance(msg, dict) else msg.content
            role_label = "用户" if role == "user" else "助手"
            text = content[:200] if len(content) > 200 else content
            lines.append(f"{role_label}：{text}")
        return "\n".join(lines)
