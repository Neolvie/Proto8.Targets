"""Integration-тесты для API обратной связи (оценок)."""

import pytest
from fastapi.testclient import TestClient


class TestApiFeedback:
    """Тесты endpoint POST /api/feedback."""

    def test_save_positive_feedback(self, app_client):
        """Положительная оценка сохраняется успешно."""
        resp = app_client.post(
            "/api/feedback",
            json={"case_id": 1, "session_id": "sess_001", "vote": 1},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_save_negative_feedback(self, app_client):
        """Отрицательная оценка сохраняется успешно."""
        resp = app_client.post(
            "/api/feedback",
            json={"case_id": 2, "session_id": "sess_002", "vote": -1},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_invalid_vote_returns_422(self, app_client):
        """Недопустимое значение vote возвращает 422."""
        resp = app_client.post(
            "/api/feedback",
            json={"case_id": 1, "session_id": "sess_003", "vote": 0},
        )
        assert resp.status_code == 422

    def test_invalid_case_id_too_large_returns_422(self, app_client):
        """case_id > 7 возвращает 422."""
        resp = app_client.post(
            "/api/feedback",
            json={"case_id": 8, "session_id": "sess_004", "vote": 1},
        )
        assert resp.status_code == 422

    def test_invalid_case_id_too_small_returns_422(self, app_client):
        """case_id < 1 возвращает 422."""
        resp = app_client.post(
            "/api/feedback",
            json={"case_id": 0, "session_id": "sess_005", "vote": 1},
        )
        assert resp.status_code == 422

    def test_update_feedback_same_session(self, app_client):
        """Повторная оценка от той же сессии обновляется без ошибок."""
        resp1 = app_client.post(
            "/api/feedback",
            json={"case_id": 3, "session_id": "sess_update", "vote": 1},
        )
        assert resp1.status_code == 200

        resp2 = app_client.post(
            "/api/feedback",
            json={"case_id": 3, "session_id": "sess_update", "vote": -1},
        )
        assert resp2.status_code == 200

    def test_feedback_reflected_in_metrics(self, app_client):
        """Оценка отображается в метриках бэк-офиса."""
        app_client.post(
            "/api/feedback",
            json={"case_id": 5, "session_id": "sess_metrics_test", "vote": 1},
        )

        resp = app_client.get("/api/metrics")
        assert resp.status_code == 200
        metrics = resp.json()
        case5 = next(c for c in metrics["case_stats"] if c["case_id"] == 5)
        assert case5["positive"] >= 1
