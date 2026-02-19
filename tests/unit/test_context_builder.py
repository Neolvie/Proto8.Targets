"""Тесты для сервиса построения контекста (context_builder)."""

import pytest
from src.services import context_builder
from src.models.targets import (
    GoalNode, TargetsMap, TargetDetail, KeyResult,
    ResponsiblePerson, StructuralUnitInfo, PeriodInfo, GoalStatus
)


@pytest.fixture
def sample_map_info():
    """Пример информации о карте."""
    return TargetsMap(
        Id=1,
        Name="Тестовая карта целей",
        Code="MAP-2026",
        PeriodLabel="2026",
        AchievementPercentage=45.5,
        Status="InProgress"
    )


@pytest.fixture
def sample_nodes():
    """Пример списка узлов целей."""
    return [
        GoalNode(
            TargetId=1,
            Code="T-1",
            Name="Цель 1",
            ParentId=None,
            ChildIds=[2],
            Priority="High",
            Progress=50.0,
            KeyResultCount=3,
            Responsible=ResponsiblePerson(Id=101, Name="Иванов И.И."),
            StructuralUnit=StructuralUnitInfo(Id=10, Name="Отдел А"),
            Period=PeriodInfo(Name="Q1 2026"),
            Status=GoalStatus(State="InProgress", Name="В работе")
        ),
        GoalNode(
            TargetId=2,
            Code="T-2",
            Name="Цель 2",
            ParentId="1",
            ChildIds=[],
            Priority="Medium",
            Progress=30.0,
            KeyResultCount=2,
            Responsible=ResponsiblePerson(Id=102, Name="Петров П.П."),
            StructuralUnit=StructuralUnitInfo(Id=11, Name="Отдел Б"),
            Period=PeriodInfo(Name="Q1 2026"),
            Status=GoalStatus(State="InProgress", Name="В работе")
        )
    ]


@pytest.fixture
def sample_target():
    """Пример детальной информации по цели."""
    return TargetDetail(
        Id=1,
        Name="Тестовая цель",
        Code="T-1",
        StatusDescription="В работе",
        PeriodLabel="Q1 2026",
        AchievementPercentage=50.0,
        PeriodStart="2026-01-01",
        PeriodEnd="2026-03-31",
        IsPersonal=False,
        Description="Это описание цели",
        Notes="Заметки руководства",
        Priority="High"
    )


@pytest.fixture
def sample_key_results():
    """Пример ключевых результатов."""
    return [
        KeyResult(
            Description="Увеличить продажи на 20%",
            AchievementPercentage="50",
            Metric="Процент роста",
            InitialValue="100",
            PlannedValue="120",
            ActualValue="110"
        ),
        KeyResult(
            Description="Снизить издержки на 10%",
            AchievementPercentage="30",
            Metric="Процент снижения",
            InitialValue="1000",
            PlannedValue="900",
            ActualValue="950"
        )
    ]


class TestNormalizeText:
    """Тесты для функции normalize_text."""

    def test_normalizes_escape_sequences(self):
        """Заменяет escape-последовательности на реальные символы."""
        text = "Строка\\nс\\nпереносами\\nи\\\\слешом"
        result = context_builder.normalize_text(text)
        assert "\n" in result
        assert "\\n" not in result
        assert "\\" in result  # одинарный слеш от \\

    def test_removes_carriage_return(self):
        """Удаляет \\r из текста."""
        text = "Текст\\rс\\rкаретками"
        result = context_builder.normalize_text(text)
        assert "\\r" not in result

    def test_returns_empty_for_none(self):
        """Возвращает пустую строку для None."""
        assert context_builder.normalize_text(None) == ""


class TestBuildMapContext:
    """Тесты для функции build_map_context."""

    def test_includes_map_header(self, sample_nodes, sample_map_info):
        """Контекст содержит заголовок карты."""
        result = context_builder.build_map_context(sample_nodes, sample_map_info)
        assert "Карта целей: Тестовая карта целей" in result
        assert "Период: 2026" in result
        assert "Прогресс: 45.5%" in result

    def test_includes_all_nodes(self, sample_nodes, sample_map_info):
        """Контекст содержит все узлы целей."""
        result = context_builder.build_map_context(sample_nodes, sample_map_info)
        assert "[T-1] Цель 1" in result
        assert "[T-2] Цель 2" in result

    def test_includes_responsible_and_unit(self, sample_nodes, sample_map_info):
        """Контекст содержит ответственных и подразделения."""
        result = context_builder.build_map_context(sample_nodes, sample_map_info)
        assert "Иванов И.И." in result
        assert "Петров П.П." in result
        assert "Отдел А" in result
        assert "Отдел Б" in result

    def test_includes_progress_and_kr_count(self, sample_nodes, sample_map_info):
        """Контекст содержит прогресс и количество КР."""
        result = context_builder.build_map_context(sample_nodes, sample_map_info)
        assert "Прогресс: 50.0%" in result
        assert "КР: 3" in result
        assert "Прогресс: 30.0%" in result
        assert "КР: 2" in result


class TestBuildTargetContext:
    """Тесты для функции build_target_context."""

    def test_includes_target_header(self, sample_target, sample_key_results):
        """Контекст содержит заголовок цели."""
        result = context_builder.build_target_context(sample_target, sample_key_results)
        assert "Цель: [T-1] Тестовая цель" in result
        assert "Период: Q1 2026 (2026-01-01 — 2026-03-31)" in result
        assert "Статус: В работе" in result
        assert "Прогресс: 50.0%" in result

    def test_includes_description(self, sample_target, sample_key_results):
        """Контекст содержит описание цели."""
        result = context_builder.build_target_context(sample_target, sample_key_results)
        assert "Описание:" in result
        assert "Это описание цели" in result

    def test_includes_notes(self, sample_target, sample_key_results):
        """Контекст содержит заметки руководства."""
        result = context_builder.build_target_context(sample_target, sample_key_results)
        assert "Заметки руководства:" in result
        assert "Заметки руководства" in result

    def test_includes_key_results(self, sample_target, sample_key_results):
        """Контекст содержит ключевые результаты."""
        result = context_builder.build_target_context(sample_target, sample_key_results)
        assert "Ключевые результаты:" in result
        assert "Увеличить продажи на 20%: 50%" in result
        assert "Снизить издержки на 10%: 30%" in result
        assert "Метрика: Процент роста" in result
        assert "План: 120" in result


class TestEstimateTokens:
    """Тесты для функции estimate_tokens."""

    def test_estimates_tokens_for_simple_text(self):
        """Оценивает количество токенов для простого текста."""
        text = "Это простой текст на русском языке"
        tokens = context_builder.estimate_tokens(text)
        assert tokens > 0
        assert tokens < 100  # Простой текст должен быть небольшим

    def test_estimates_tokens_for_long_text(self):
        """Оценивает количество токенов для длинного текста."""
        text = "Слово " * 500
        tokens = context_builder.estimate_tokens(text)
        assert tokens > 100  # Длинный текст должен иметь много токенов

    def test_handles_unknown_model(self):
        """Обрабатывает неизвестную модель через fallback."""
        text = "Test text"
        tokens = context_builder.estimate_tokens(text, model="unknown-model-xyz")
        assert tokens > 0  # Должен использовать fallback encoding
