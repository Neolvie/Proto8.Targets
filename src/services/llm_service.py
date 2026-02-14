"""Сервис для взаимодействия с LLM через OpenAI Python SDK."""

from typing import AsyncGenerator
from openai import AsyncOpenAI, APIStatusError
from src.config import get_openai_api_key, get_openai_model, get_openai_server


def _create_client() -> AsyncOpenAI:
    """
    Создаёт клиент OpenAI с настройками из переменных окружения.

    Returns:
        AsyncOpenAI: Асинхронный клиент OpenAI.
    """
    api_key = get_openai_api_key()
    base_url = get_openai_server()

    kwargs = {"api_key": api_key or "dummy"}
    if base_url:
        kwargs["base_url"] = base_url

    return AsyncOpenAI(**kwargs)


async def stream_completion(
    messages: list[dict],
    model: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    Генерирует текст через OpenAI API с потоковой передачей (streaming).

    Args:
        messages: Список сообщений в формате [{role, content}].
        model: Название модели (если None — берётся из конфигурации).

    Yields:
        str: Фрагменты текста ответа по мере генерации.

    Raises:
        ValueError: Если превышен лимит контекста модели.
        RuntimeError: При других ошибках API.
    """
    client = _create_client()
    model_name = model or get_openai_model()

    try:
        stream = await client.chat.completions.create(
            model=model_name,
            messages=messages,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    except APIStatusError as e:
        if e.status_code == 400 and "context_length_exceeded" in str(e.body).lower():
            raise ValueError(
                "Карта целей слишком большая для обработки. "
                "Попробуйте загрузить часть целей или выбрать конкретную цель."
            ) from e
        raise RuntimeError(f"Ошибка OpenAI API: {e.message}") from e
    except Exception as e:
        if "context_length_exceeded" in str(e).lower() or "maximum context" in str(e).lower():
            raise ValueError(
                "Карта целей слишком большая для обработки. "
                "Попробуйте загрузить часть целей или выбрать конкретную цель."
            ) from e
        raise RuntimeError(f"Ошибка при обращении к LLM: {e}") from e
