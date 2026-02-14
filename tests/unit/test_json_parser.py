"""Unit-тесты для парсера JSON карты целей."""

import json
import pytest
from src.services.json_parser import parse_goals_map, format_map_for_llm, get_goal_by_id


class TestParseGoalsMap:
    """Тесты функции parse_goals_map."""

    def test_parse_valid_json(self, sample_json_text):
        """Парсинг корректного JSON с двумя целями."""
        result = parse_goals_map(sample_json_text)
        assert result.map_name == "Тестовая карта целей"
        assert len(result.nodes) == 2
        assert result.total_progress == 40.0

    def test_parse_nodes_fields(self, sample_json_text):
        """Проверка корректности полей узла."""
        result = parse_goals_map(sample_json_text)
        root = next(n for n in result.nodes if n.id == "1")
        assert root.code == "U-26.4.1"
        assert root.name == "Тестовая цель верхнего уровня"
        assert root.priority == "High"
        assert root.progress == 50.0
        assert root.responsible_name == "Иванов Иван"
        assert root.period_name == "2026 год"
        assert root.key_result_count == 3
        assert root.last_achievement_description == "Идёт по плану"
        assert root.parent_id is None
        assert root.child_ids == ["2"]

    def test_parse_child_node(self, sample_json_text):
        """Проверка дочернего узла."""
        result = parse_goals_map(sample_json_text)
        child = next(n for n in result.nodes if n.id == "2")
        assert child.parent_id == "1"
        assert child.child_ids == []
        assert child.last_achievement_description is None

    def test_parse_without_payload_wrapper(self):
        """Парсинг JSON без обёртки Payload (прямой массив Nodes)."""
        raw = {
            "Nodes": [
                {
                    "Id": "5", "TargetId": 5, "Code": "TEST",
                    "Name": "Тест", "ParentId": None, "ChildIds": [],
                    "Priority": "Low", "Progress": 0.0, "KeyResultCount": 0,
                    "Status": {"State": "Active", "Name": "В работе", "Icon": None, "LastAchievementStatus": None},
                    "Responsible": {"Name": "Тестов"}, "StructuralUnit": {"Name": "Тест"},
                    "Period": {"Name": "2026", "TimeFrame": "Year"}
                }
            ]
        }
        result = parse_goals_map(json.dumps(raw))
        assert len(result.nodes) == 1
        assert result.nodes[0].id == "5"

    def test_parse_invalid_json(self):
        """Невалидный JSON вызывает ValueError."""
        with pytest.raises(ValueError, match="Невалидный JSON"):
            parse_goals_map("not a json {{{")

    def test_parse_missing_nodes(self):
        """JSON без поля Nodes вызывает ValueError."""
        with pytest.raises(ValueError, match="Не найдено поле 'Nodes'"):
            parse_goals_map(json.dumps({"Payload": {"Map": {}}}))

    def test_parse_empty_nodes(self):
        """JSON с пустым массивом Nodes парсится без ошибок."""
        raw = json.dumps({"Payload": {"Nodes": [], "Map": {"Name": "Пустая", "Progress": 0}}})
        result = parse_goals_map(raw)
        assert result.nodes == []

    def test_parse_non_dict_root(self):
        """Не-объектный JSON вызывает ValueError."""
        with pytest.raises(ValueError):
            parse_goals_map("[1, 2, 3]")

    def test_parse_real_ario_json(self):
        """Интеграционный тест: парсинг реального Ario.json если он доступен."""
        import os
        path = os.path.join("data", "Ario.json")
        if not os.path.exists(path):
            pytest.skip("Ario.json недоступен")
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        result = parse_goals_map(text)
        assert len(result.nodes) > 0


class TestFormatMapForLlm:
    """Тесты функции format_map_for_llm."""

    def test_format_basic(self, sample_json_text):
        """Форматирование карты в текст для LLM."""
        goals_map = parse_goals_map(sample_json_text)
        text = format_map_for_llm(goals_map)
        assert "Тестовая карта целей" in text
        assert "U-26.4.1" in text
        assert "Тестовая цель верхнего уровня" in text

    def test_format_highlights_selected_goal(self, sample_json_text):
        """Выбранная цель выделяется маркером ВЫБРАННАЯ ЦЕЛЬ."""
        goals_map = parse_goals_map(sample_json_text)
        text = format_map_for_llm(goals_map, selected_goal_id="1")
        assert "ВЫБРАННАЯ ЦЕЛЬ" in text

    def test_format_without_selected(self, sample_json_text):
        """Без выбранной цели маркер отсутствует."""
        goals_map = parse_goals_map(sample_json_text)
        text = format_map_for_llm(goals_map)
        assert "ВЫБРАННАЯ ЦЕЛЬ" not in text


class TestGetGoalById:
    """Тесты функции get_goal_by_id."""

    def test_found(self, sample_json_text):
        """Цель находится по корректному ID."""
        goals_map = parse_goals_map(sample_json_text)
        goal = get_goal_by_id(goals_map, "1")
        assert goal is not None
        assert goal.code == "U-26.4.1"

    def test_not_found(self, sample_json_text):
        """Несуществующий ID возвращает None."""
        goals_map = parse_goals_map(sample_json_text)
        goal = get_goal_by_id(goals_map, "999")
        assert goal is None
