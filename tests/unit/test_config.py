"""Unit-тесты для модуля config."""

import os
import pytest
from unittest.mock import patch
from src import config


class TestGetOpenAIApiKey:
    """Тесты для get_openai_api_key()."""

    def test_returns_key_from_env(self):
        """Возвращает ключ из переменной окружения."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}):
            assert config.get_openai_api_key() == "test_key"

    def test_returns_empty_if_not_set(self):
        """Возвращает пустую строку если переменная не установлена."""
        with patch.dict(os.environ, {}, clear=True):
            assert config.get_openai_api_key() == ""


class TestGetOpenAIModel:
    """Тесты для get_openai_model()."""

    def test_returns_model_from_env(self):
        """Возвращает модель из переменной окружения."""
        with patch.dict(os.environ, {"OPENAI_MODEL": "gpt-3.5-turbo"}):
            assert config.get_openai_model() == "gpt-3.5-turbo"

    def test_returns_default_model(self):
        """Возвращает модель по умолчанию если переменная не установлена."""
        with patch.dict(os.environ, {}, clear=True):
            assert config.get_openai_model() == "gpt-4o"


class TestGetOpenAIServer:
    """Тесты для get_openai_server()."""

    def test_returns_server_from_env(self):
        """Возвращает кастомный сервер из переменной окружения."""
        with patch.dict(os.environ, {"OPENAI_SERVER": "https://custom.api.com"}):
            assert config.get_openai_server() == "https://custom.api.com"

    def test_returns_none_if_not_set(self):
        """Возвращает None если переменная не установлена."""
        with patch.dict(os.environ, {}, clear=True):
            assert config.get_openai_server() is None


class TestGetDataDir:
    """Тесты для get_data_dir()."""

    def test_returns_data_dir_from_env(self):
        """Возвращает путь к данным из переменной окружения."""
        with patch.dict(os.environ, {"DATA_DIR": "/custom/data"}):
            assert config.get_data_dir() == "/custom/data"

    def test_returns_default_data_dir(self):
        """Возвращает путь по умолчанию если переменная не установлена."""
        with patch.dict(os.environ, {}, clear=True):
            assert config.get_data_dir() == "/app/data"


class TestGetPort:
    """Тесты для get_port()."""

    def test_returns_port_from_env(self):
        """Возвращает порт из переменной окружения."""
        with patch.dict(os.environ, {"PORT": "3000"}):
            assert config.get_port() == 3000

    def test_returns_default_port(self):
        """Возвращает порт по умолчанию если переменная не установлена."""
        with patch.dict(os.environ, {}, clear=True):
            assert config.get_port() == 8000


class TestGetTargetsBaseUrl:
    """Тесты для get_targets_base_url()."""

    def test_returns_url_from_env(self):
        """Возвращает URL из переменной окружения."""
        with patch.dict(os.environ, {"TARGETS_BASE_URL": "https://targets.example.com"}):
            assert config.get_targets_base_url() == "https://targets.example.com"

    def test_returns_none_if_not_set(self):
        """Возвращает None если переменная не установлена."""
        with patch.dict(os.environ, {}, clear=True):
            assert config.get_targets_base_url() is None


class TestGetTargetsToken:
    """Тесты для get_targets_token()."""

    def test_returns_token_from_env(self):
        """Возвращает токен из переменной окружения."""
        with patch.dict(os.environ, {"TARGETS_TOKEN": "bearer_token_123"}):
            assert config.get_targets_token() == "bearer_token_123"

    def test_returns_none_if_not_set(self):
        """Возвращает None если переменная не установлена."""
        with patch.dict(os.environ, {}, clear=True):
            assert config.get_targets_token() is None
