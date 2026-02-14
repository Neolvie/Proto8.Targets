"""Integration-тесты для API метрик бэк-офиса."""

import pytest


class TestApiMetrics:
    """Тесты endpoint GET /api/metrics."""

    def test_metrics_returns_200(self, app_client):
        """Метрики возвращаются с кодом 200."""
        resp = app_client.get("/api/metrics")
        assert resp.status_code == 200

    def test_metrics_structure(self, app_client):
        """Ответ содержит все необходимые поля."""
        resp = app_client.get("/api/metrics")
        data = resp.json()
        assert "total_requests" in data
        assert "unique_ips" in data
        assert "ip_stats" in data
        assert "case_stats" in data
        assert "timeline" in data
        assert "total_positive_pct" in data

    def test_case_stats_count(self, app_client):
        """Статистика кейсов содержит 7 элементов."""
        resp = app_client.get("/api/metrics")
        data = resp.json()
        assert len(data["case_stats"]) == 7

    def test_case_stats_fields(self, app_client):
        """Каждый элемент статистики кейсов содержит нужные поля."""
        resp = app_client.get("/api/metrics")
        data = resp.json()
        for case in data["case_stats"]:
            assert "case_id" in case
            assert "requests" in case
            assert "positive" in case
            assert "negative" in case
            assert "pct_positive" in case

    def test_requests_counted_in_metrics(self, app_client, sample_json_text):
        """Запрос к /api/data/upload отображается в метриках."""
        # Делаем запрос
        app_client.post(
            "/api/data/upload",
            data={"json_text": sample_json_text},
        )

        resp = app_client.get("/api/metrics")
        data = resp.json()
        assert data["total_requests"] >= 1


class TestApiHealth:
    """Тесты healthcheck endpoint."""

    def test_health_returns_200(self, app_client):
        """Healthcheck возвращает 200."""
        resp = app_client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestStaticPages:
    """Тесты раздачи статических страниц."""

    def test_index_returns_200(self, app_client):
        """Главная страница / возвращает 200."""
        resp = app_client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_backoffice_returns_200(self, app_client):
        """Страница /backoffice возвращает 200."""
        resp = app_client.get("/backoffice")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_index_contains_targets_title(self, app_client):
        """Главная страница содержит заголовок приложения."""
        resp = app_client.get("/")
        assert "Targets" in resp.text or "Directum" in resp.text

    def test_backoffice_contains_metrics_title(self, app_client):
        """Страница бэк-офиса содержит заголовок метрик."""
        resp = app_client.get("/backoffice")
        assert "Метрик" in resp.text or "backoffice" in resp.text.lower()
