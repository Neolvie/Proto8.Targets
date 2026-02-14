"""Конфигурация Playwright E2E тестов."""

import pytest


BASE_URL = "http://localhost:8000"


@pytest.fixture(scope="session")
def base_url():
    """Базовый URL приложения для E2E тестов."""
    return BASE_URL
