"""Интеграционные тесты для v2 API endpoints."""

import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Тесты для /api/health."""

    def test_health_returns_ok(self):
        """Health endpoint возвращает статус ok."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data


class TestMapsEndpoint:
    """Тесты для /api/maps."""

    def test_maps_without_config_returns_error(self):
        """Без настройки API возвращает ошибку и пустые списки."""
        response = client.get("/api/maps")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["maps"] == []
        assert data["periods"] == []


class TestMainPage:
    """Тесты для главной страницы."""

    def test_index_returns_html(self):
        """Главная страница возвращает HTML."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Directum Targets" in response.text

    def test_backoffice_returns_html(self):
        """Страница бэк-офиса возвращает HTML."""
        response = client.get("/backoffice")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestMetricsEndpoint:
    """Тесты для /api/metrics."""

    def test_metrics_returns_structure(self):
        """Метрики возвращают корректную структуру."""
        response = client.get("/api/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data
        assert "unique_ips" in data
        assert "case_stats" in data
        assert isinstance(data["case_stats"], list)
