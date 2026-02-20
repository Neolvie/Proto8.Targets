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


