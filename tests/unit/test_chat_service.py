"""Unit-тесты для сервиса свободного чата."""

import pytest
from unittest.mock import patch
from src.services.json_parser import parse_goals_map
from src.services import chat_service
from src.models.api import ChatMessage


@pytest.fixture
def goals_map(sample_json_text):
    """Возвращает объект GoalsMap из тестового JSON."""
    return parse_goals_map(sample_json_text)


class TestRunChat:
    """Тесты функции run_chat."""

    @pytest.mark.asyncio
    async def test_chat_returns_generator(self, goals_map):
        """Функция run_chat возвращает асинхронный генератор."""
        async def mock_stream(messages, model=None):
            yield "Ответ чата"

        with patch("src.services.chat_service.llm_service.stream_completion", side_effect=mock_stream):
            messages = [ChatMessage(role="user", content="Расскажи про цели")]
            gen = await chat_service.run_chat(goals_map, messages)
            chunks = []
            async for chunk in gen:
                chunks.append(chunk)
            assert "Ответ чата" in "".join(chunks)

    @pytest.mark.asyncio
    async def test_chat_without_messages(self, goals_map):
        """Чат с пустой историей сообщений работает."""
        async def mock_stream(messages, model=None):
            yield "Привет!"

        with patch("src.services.chat_service.llm_service.stream_completion", side_effect=mock_stream):
            gen = await chat_service.run_chat(goals_map, [])
            chunks = [chunk async for chunk in gen]
            assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_chat_includes_map_context(self, goals_map):
        """Системный промпт содержит контекст карты целей."""
        captured_messages = []

        async def capture_stream(messages, model=None):
            captured_messages.extend(messages)
            yield "OK"

        with patch("src.services.chat_service.llm_service.stream_completion", side_effect=capture_stream):
            messages = [ChatMessage(role="user", content="Вопрос")]
            gen = await chat_service.run_chat(goals_map, messages)
            async for _ in gen:
                pass

        # Системный промпт должен включать карту целей
        system_msg = captured_messages[0]
        assert system_msg["role"] == "system"
        assert "Тестовая карта целей" in system_msg["content"] or "U-26.4.1" in system_msg["content"]

    @pytest.mark.asyncio
    async def test_chat_includes_docx_context(self, goals_map):
        """Системный промпт включает DOCX контент если передан."""
        captured_messages = []

        async def capture_stream(messages, model=None):
            captured_messages.extend(messages)
            yield "OK"

        with patch("src.services.chat_service.llm_service.stream_completion", side_effect=capture_stream):
            messages = [ChatMessage(role="user", content="Вопрос")]
            gen = await chat_service.run_chat(goals_map, messages, docx_content="Важная информация из DOCX")
            async for _ in gen:
                pass

        system_msg = captured_messages[0]
        assert "Важная информация из DOCX" in system_msg["content"]

    @pytest.mark.asyncio
    async def test_chat_passes_message_history(self, goals_map):
        """История сообщений передаётся в LLM в правильном порядке."""
        captured_messages = []

        async def capture_stream(messages, model=None):
            captured_messages.extend(messages)
            yield "OK"

        with patch("src.services.chat_service.llm_service.stream_completion", side_effect=capture_stream):
            history = [
                ChatMessage(role="user", content="Первый вопрос"),
                ChatMessage(role="assistant", content="Первый ответ"),
                ChatMessage(role="user", content="Второй вопрос"),
            ]
            gen = await chat_service.run_chat(goals_map, history)
            async for _ in gen:
                pass

        # Системный промпт + 3 сообщения истории
        assert len(captured_messages) == 4
        assert captured_messages[1]["role"] == "user"
        assert captured_messages[1]["content"] == "Первый вопрос"
        assert captured_messages[3]["content"] == "Второй вопрос"
