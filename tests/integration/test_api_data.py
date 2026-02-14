"""Integration-тесты для API загрузки данных."""

import os
import json
import shutil
import pytest
from fastapi.testclient import TestClient


class TestApiDataTest:
    """Тесты endpoint GET /api/data/test."""

    def test_returns_404_when_no_test_file(self, app_client, temp_data_dir):
        """404 если тестовые файлы не скопированы."""
        resp = app_client.get("/api/data/test")
        assert resp.status_code == 404

    def test_returns_data_when_file_exists(self, app_client, temp_data_dir, sample_json_text):
        """200 и корректные данные если Ario.json скопирован."""
        json_path = os.path.join(temp_data_dir, "Ario.json")
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(sample_json_text)

        resp = app_client.get("/api/data/test")
        assert resp.status_code == 200
        data = resp.json()
        assert "goals_map" in data
        assert "goals_list" in data
        assert len(data["goals_list"]) == 2


class TestApiDataUpload:
    """Тесты endpoint POST /api/data/upload."""

    def test_upload_json_text(self, app_client, sample_json_text):
        """Загрузка JSON через текстовое поле."""
        resp = app_client.post(
            "/api/data/upload",
            data={"json_text": sample_json_text},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["goals_map"]["map_name"] == "Тестовая карта целей"
        assert len(data["goals_list"]) == 2

    def test_upload_json_file(self, app_client, sample_json_text):
        """Загрузка JSON через файл."""
        files = {"json_file": ("test.json", sample_json_text.encode(), "application/json")}
        resp = app_client.post("/api/data/upload", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert "goals_map" in data

    def test_upload_without_data_returns_422(self, app_client):
        """Запрос без данных возвращает 422."""
        resp = app_client.post("/api/data/upload", data={})
        assert resp.status_code == 422

    def test_upload_invalid_json_returns_422(self, app_client):
        """Невалидный JSON возвращает 422."""
        resp = app_client.post(
            "/api/data/upload",
            data={"json_text": "this is not json"},
        )
        assert resp.status_code == 422

    def test_upload_json_without_nodes_returns_422(self, app_client):
        """JSON без поля Nodes возвращает 422."""
        bad_json = json.dumps({"Payload": {"Map": {}}})
        resp = app_client.post(
            "/api/data/upload",
            data={"json_text": bad_json},
        )
        assert resp.status_code == 422

    def test_upload_goals_list_fields(self, app_client, sample_json_text):
        """Список целей содержит необходимые поля."""
        resp = app_client.post(
            "/api/data/upload",
            data={"json_text": sample_json_text},
        )
        data = resp.json()
        goal = data["goals_list"][0]
        assert "id" in goal
        assert "code" in goal
        assert "name" in goal
        assert "progress" in goal
