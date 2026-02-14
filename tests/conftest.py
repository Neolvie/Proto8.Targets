"""Общие фикстуры для тестов."""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def temp_data_dir():
    """Создаёт временную директорию для тестовых данных и БД."""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture(autouse=True)
def set_test_data_dir(temp_data_dir, monkeypatch):
    """Устанавливает временную директорию для данных в тестах."""
    monkeypatch.setenv("DATA_DIR", temp_data_dir)


@pytest.fixture(scope="session")
def sample_json_text():
    """Возвращает минимальный валидный JSON карты целей."""
    return '''{
      "Payload": {
        "Nodes": [
          {
            "Id": "1",
            "TargetId": 1,
            "Code": "U-26.4.1",
            "Name": "Тестовая цель верхнего уровня",
            "ParentId": null,
            "ChildIds": ["2"],
            "Priority": "High",
            "Progress": 50.0,
            "KeyResultCount": 3,
            "Status": {
              "State": "Active",
              "Name": "В работе",
              "Icon": "Green",
              "LastAchievementStatus": {
                "Description": "Идёт по плану",
                "ReportDate": "2026-01-15T00:00:00Z"
              }
            },
            "Responsible": {"Name": "Иванов Иван"},
            "StructuralUnit": {"Name": "БЕ Ario"},
            "Period": {"Name": "2026 год", "TimeFrame": "Year"}
          },
          {
            "Id": "2",
            "TargetId": 2,
            "Code": "U-1Q26.1-1",
            "Name": "Дочерняя тестовая цель",
            "ParentId": "1",
            "ChildIds": [],
            "Priority": "Medium",
            "Progress": 30.0,
            "KeyResultCount": 2,
            "Status": {
              "State": "Active",
              "Name": "В работе",
              "Icon": null,
              "LastAchievementStatus": null
            },
            "Responsible": {"Name": "Петров Пётр"},
            "StructuralUnit": {"Name": "БЕ Ario"},
            "Period": {"Name": "I квартал 2026", "TimeFrame": "Quarter"}
          }
        ],
        "Map": {
          "Id": 1,
          "Name": "Тестовая карта целей",
          "Progress": 40.0
        }
      }
    }'''


@pytest.fixture
def app_client(temp_data_dir):
    """Создаёт тестовый клиент FastAPI."""
    import src.services.metrics_storage as ms
    ms.init_db()

    from src.main import app
    with TestClient(app) as client:
        yield client
