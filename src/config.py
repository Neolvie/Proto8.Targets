"""Конфигурация приложения из переменных окружения."""

import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)


def get_openai_api_key() -> str:
    """Возвращает ключ API OpenAI из переменных окружения."""
    key = os.getenv("OPENAI_API_KEY", "")
    return key


def get_openai_model() -> str:
    """Возвращает название модели OpenAI из переменных окружения."""
    return os.getenv("OPENAI_MODEL", "gpt-4o")


def get_openai_server() -> str | None:
    """Возвращает кастомный endpoint OpenAI или None если не задан."""
    server = os.getenv("OPENAI_SERVER", "").strip()
    return server if server else None


def get_data_dir() -> str:
    """Возвращает путь к директории с данными."""
    return os.getenv("DATA_DIR", "/app/data")


def get_port() -> int:
    """Возвращает порт приложения."""
    return int(os.getenv("PORT", "8000"))


def get_targets_base_url() -> str | None:
    """Возвращает базовый URL Directum Targets API."""
    url = os.getenv("TARGETS_BASE_URL", "").strip()
    return url if url else None


def get_targets_token() -> str | None:
    """Возвращает Bearer-токен для Directum Targets API."""
    token = os.getenv("TARGETS_TOKEN", "").strip()
    return token if token else None


def get_backoffice_credentials() -> tuple[str, str]:
    """Возвращает (логин, пароль) для Basic Auth бэкофиса."""
    user = os.getenv("BACKOFFICE_USER", "admin").strip()
    password = os.getenv("BACKOFFICE_PASSWORD", "admin").strip()
    return user, password
