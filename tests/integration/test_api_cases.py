"""Integration-тесты для API кейсов OKR-анализа."""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


def make_case_body(sample_json_text, selected_goal_id=None):
    """Создаёт тело запроса для кейса из тестового JSON."""
    from src.services.json_parser import parse_goals_map
    goals_map = parse_goals_map(sample_json_text)
    return {
        "goals_map": goals_map.model_dump(),
        "selected_goal_id": selected_goal_id,
        "docx_content": None,
    }


async def mock_stream_gen(messages, model=None):
    """Асинхронный генератор для mock LLM ответа."""
    yield "Тестовый ответ"


class TestApiCases:
    """Тесты endpoint POST /api/cases/{case_id}."""

    def test_case_id_out_of_range_returns_400(self, app_client, sample_json_text):
        """case_id = 0 или 8 возвращает 400."""
        body = make_case_body(sample_json_text)
        resp = app_client.post("/api/cases/0", json=body)
        assert resp.status_code == 400

        resp = app_client.post("/api/cases/8", json=body)
        assert resp.status_code == 400

    def test_case1_without_goal_returns_422(self, app_client, sample_json_text):
        """Кейс 1 без выбранной цели возвращает 422."""
        body = make_case_body(sample_json_text, selected_goal_id=None)
        resp = app_client.post("/api/cases/1", json=body)
        assert resp.status_code == 422

    def test_case5_returns_streaming_response(self, app_client, sample_json_text):
        """Кейс 5 (не требует цели) возвращает SSE поток."""
        with patch(
            "src.services.cases_service.llm_service.stream_completion",
            side_effect=mock_stream_gen
        ):
            body = make_case_body(sample_json_text)
            resp = app_client.post("/api/cases/5", json=body)
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]

    def test_case7_returns_streaming_response(self, app_client, sample_json_text):
        """Кейс 7 (не требует цели) возвращает SSE поток."""
        with patch(
            "src.services.cases_service.llm_service.stream_completion",
            side_effect=mock_stream_gen
        ):
            body = make_case_body(sample_json_text)
            resp = app_client.post("/api/cases/7", json=body)
            assert resp.status_code == 200

    def test_case1_with_valid_goal_returns_streaming(self, app_client, sample_json_text):
        """Кейс 1 с корректной целью возвращает SSE поток."""
        with patch(
            "src.services.cases_service.llm_service.stream_completion",
            side_effect=mock_stream_gen
        ):
            body = make_case_body(sample_json_text, selected_goal_id="1")
            resp = app_client.post("/api/cases/1", json=body)
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]

    def test_sse_response_contains_done(self, app_client, sample_json_text):
        """SSE поток завершается маркером [DONE]."""
        with patch(
            "src.services.cases_service.llm_service.stream_completion",
            side_effect=mock_stream_gen
        ):
            body = make_case_body(sample_json_text)
            resp = app_client.post("/api/cases/5", json=body)
            content = resp.text
            assert "[DONE]" in content

    def test_case_request_logged_to_metrics(self, app_client, sample_json_text):
        """Запуск кейса логируется в метриках."""
        with patch(
            "src.services.cases_service.llm_service.stream_completion",
            side_effect=mock_stream_gen
        ):
            body = make_case_body(sample_json_text)
            app_client.post("/api/cases/7", json=body)

        metrics_resp = app_client.get("/api/metrics")
        metrics = metrics_resp.json()
        case7 = next(c for c in metrics["case_stats"] if c["case_id"] == 7)
        assert case7["requests"] >= 1
