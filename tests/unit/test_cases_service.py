"""Unit-тесты для сервиса кейсов OKR-анализа."""

import pytest
from unittest.mock import patch, AsyncMock
from src.services.json_parser import parse_goals_map
from src.services import cases_service


@pytest.fixture
def goals_map(sample_json_text):
    """Возвращает объект GoalsMap из тестового JSON."""
    return parse_goals_map(sample_json_text)


class TestRunCase:
    """Тесты функции run_case."""

    async def test_invalid_case_id_raises(self, goals_map):
        """Несуществующий кейс (0 или 8) вызывает ValueError."""
        with pytest.raises(ValueError, match="не существует"):
            await cases_service.run_case(0, goals_map, None, None)

        with pytest.raises(ValueError, match="не существует"):
            await cases_service.run_case(8, goals_map, None, None)

    @pytest.mark.parametrize("case_id", [1, 2, 3, 4, 6])
    async def test_cases_1_to_4_6_require_goal(self, goals_map, case_id):
        """Кейсы 1-4 и 6 требуют выбранную цель."""
        with pytest.raises(ValueError, match="необходимо выбрать цель"):
            await cases_service.run_case(case_id, goals_map, None, None)

    @pytest.mark.parametrize("case_id", [1, 2, 3, 4, 6])
    async def test_case_with_unknown_goal_id_raises(self, goals_map, case_id):
        """Кейсы с несуществующим goal_id выбрасывают ValueError."""
        with pytest.raises(ValueError, match="не найдена"):
            await cases_service.run_case(case_id, goals_map, "nonexistent_999", None)

    async def test_case5_works_without_goal(self, goals_map):
        """Кейс 5 (конфликты) не требует выбранную цель."""
        async def mock_stream(messages, model=None):
            yield "Тестовый ответ кейса 5"

        with patch("src.services.llm_service.stream_completion", side_effect=mock_stream):
            gen = await cases_service.run_case(5, goals_map, None, None)
            chunks = []
            async for chunk in gen:
                chunks.append(chunk)
            assert len(chunks) > 0
            assert "Тестовый ответ кейса 5" in "".join(chunks)

    async def test_case7_works_without_goal(self, goals_map):
        """Кейс 7 (экспресс-отчёт) не требует выбранную цель."""
        async def mock_stream(messages, model=None):
            yield "Экспресс-отчёт кейса 7"

        with patch("src.services.llm_service.stream_completion", side_effect=mock_stream):
            gen = await cases_service.run_case(7, goals_map, None, None)
            chunks = []
            async for chunk in gen:
                chunks.append(chunk)
            assert len(chunks) > 0

    @pytest.mark.parametrize("case_id", [1, 2, 3, 4, 6])
    async def test_cases_with_valid_goal(self, goals_map, case_id):
        """Кейсы 1-4 и 6 успешно выполняются с корректной целью."""
        async def mock_stream(messages, model=None):
            yield f"Ответ кейса {case_id}"

        with patch("src.services.llm_service.stream_completion", side_effect=mock_stream):
            gen = await cases_service.run_case(case_id, goals_map, "1", None)
            chunks = []
            async for chunk in gen:
                chunks.append(chunk)
            assert len(chunks) > 0
            assert f"Ответ кейса {case_id}" in "".join(chunks)


class TestGetGoalOrRaise:
    """Тесты вспомогательной функции _get_goal_or_raise."""

    def test_no_goal_id(self, goals_map):
        """None в качестве goal_id вызывает ValueError."""
        with pytest.raises(ValueError, match="необходимо выбрать цель"):
            cases_service._get_goal_or_raise(goals_map, None)

    def test_empty_string_goal_id(self, goals_map):
        """Пустая строка вызывает ValueError."""
        with pytest.raises(ValueError, match="необходимо выбрать цель"):
            cases_service._get_goal_or_raise(goals_map, "")

    def test_valid_goal_id(self, goals_map):
        """Корректный goal_id возвращает узел цели."""
        result = cases_service._get_goal_or_raise(goals_map, "1")
        assert result.id == "1"
        assert result.code == "U-26.4.1"

    def test_invalid_goal_id(self, goals_map):
        """Несуществующий goal_id вызывает ValueError."""
        with pytest.raises(ValueError, match="не найдена"):
            cases_service._get_goal_or_raise(goals_map, "999")


class TestCasesPromptBuilding:
    """Тесты формирования промптов для кейсов."""

    def test_goal_context_includes_goal_name(self, goals_map):
        """Контекст цели включает её название."""
        goal = cases_service._get_goal_or_raise(goals_map, "1")
        ctx = cases_service._goal_context(goal, None)
        assert "Тестовая цель верхнего уровня" in ctx
        assert "U-26.4.1" in ctx

    def test_goal_context_includes_docx(self, goals_map):
        """Контекст цели включает содержимое DOCX если передан."""
        goal = cases_service._get_goal_or_raise(goals_map, "1")
        ctx = cases_service._goal_context(goal, "Тестовое описание из DOCX")
        assert "Тестовое описание из DOCX" in ctx

    def test_goal_context_without_docx(self, goals_map):
        """Контекст цели без DOCX не включает раздел DOCX."""
        goal = cases_service._get_goal_or_raise(goals_map, "1")
        ctx = cases_service._goal_context(goal, None)
        assert "из DOCX" not in ctx


class TestRunCaseV2:
    """Тесты для run_case_v2 (v2 API с текстовыми контекстами)."""

    async def test_case1_v2_requires_target_context(self):
        """Кейс 1 v2 требует target_context."""
        with pytest.raises(ValueError, match="необходимо выбрать цель"):
            await cases_service.run_case_v2(1, map_context=None, target_context=None)

    async def test_case5_v2_requires_map_context(self):
        """Кейс 5 v2 требует map_context."""
        with pytest.raises(ValueError, match="необходимо выбрать карту"):
            await cases_service.run_case_v2(5, map_context=None, target_context=None)

    async def test_case1_v2_works_with_target_context(self):
        """Кейс 1 v2 работает с target_context."""
        async def mock_stream(messages, model=None):
            yield "SMART-анализ"

        with patch("src.services.llm_service.stream_completion", side_effect=mock_stream):
            gen = await cases_service.run_case_v2(
                1,
                map_context=None,
                target_context="Цель: [T-1] Тестовая цель\nПрогресс: 50%"
            )
            chunks = []
            async for chunk in gen:
                chunks.append(chunk)
            assert len(chunks) > 0
            assert "SMART" in "".join(chunks)

    async def test_invalid_case_id_v2_raises(self):
        """Несуществующий кейс v2 выбрасывает ValueError."""
        with pytest.raises(ValueError, match="не существует"):
            await cases_service.run_case_v2(0, None, None)
