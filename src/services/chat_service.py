"""Сервис свободного чата с ИИ-помощником по карте целей."""

from typing import AsyncGenerator, Optional
from src.models.targets import GoalsMap
from src.models.api import ChatMessage
from src.services.json_parser import format_map_for_llm
from src.services import llm_service


CHAT_SYSTEM_PROMPT = """Ты — ИИ-помощник по OKR-методологии для системы Directum Targets.
Ты помогаешь пользователям анализировать карту стратегических целей, формулировать OKR, выявлять риски и конфликты.

Правила работы:
- Отвечай только на русском языке
- Используй загруженные данные (карта целей и описание цели) как основу для ответов
- Будь конкретным, аналитичным и практичным
- Если вопрос не связан с загруженными данными — всё равно отвечай, но укажи на это
- Форматируй ответы с заголовками и списками для лучшей читаемости"""


async def run_chat(
    goals_map: GoalsMap,
    messages: list[ChatMessage],
    docx_content: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    Выполняет запрос к свободному чату с ИИ-помощником.

    Формирует системный промпт с контекстом карты целей и передаёт
    историю сообщений в LLM для генерации ответа.

    Args:
        goals_map: Карта целей из Directum Targets.
        messages: История сообщений текущей сессии.
        docx_content: Содержимое DOCX-файла с описанием цели.

    Returns:
        AsyncGenerator[str, None]: Потоковый генератор фрагментов ответа.
    """
    map_text = format_map_for_llm(goals_map)

    context_parts = [
        "## Загруженные данные для анализа:",
        "",
        "### Карта целей:",
        map_text,
    ]

    if docx_content:
        context_parts.extend([
            "",
            "### Детальное описание цели (из DOCX):",
            docx_content,
        ])

    context = "\n".join(context_parts)
    system_message = f"{CHAT_SYSTEM_PROMPT}\n\n{context}"

    llm_messages = [{"role": "system", "content": system_message}]
    for msg in messages:
        llm_messages.append({"role": msg.role, "content": msg.content})

    return llm_service.stream_completion(llm_messages)
