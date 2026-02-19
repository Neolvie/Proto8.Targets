"""Сервис для выполнения 7 кейсов OKR-анализа через LLM."""

from typing import AsyncGenerator, Optional
from src.models.targets import GoalsMap, GoalNodeV1
from src.services.json_parser import format_map_for_llm, get_goal_by_id
from src.services import llm_service


SYSTEM_BASE = """Ты — ИИ-помощник по OKR-методологии для системы Directum Targets.
Ты помогаешь ответственным за цели, руководителям и аналитикам работать с картой стратегических целей.
Отвечай только на русском языке. Используй структурированный формат с заголовками и списками.
Будь конкретным, практичным и аналитичным."""


def _goal_context(goal: GoalNodeV1, docx_content: Optional[str]) -> str:
    """
    Формирует текстовый контекст выбранной цели для передачи в LLM.

    Args:
        goal: Объект цели.
        docx_content: Содержимое DOCX-файла с описанием цели.

    Returns:
        str: Форматированный контекст цели.
    """
    parts = [
        "## Выбранная цель:",
        f"Код: {goal.code}",
        f"Название: {goal.name}",
        f"Прогресс: {goal.progress:.0f}%",
        f"Статус: {goal.status_name}",
        f"Приоритет: {goal.priority}",
        f"Ответственный: {goal.responsible_name}",
        f"Период: {goal.period_name}",
        f"Ключевых результатов: {goal.key_result_count}",
    ]
    if goal.last_achievement_description:
        parts.append(f"\nПоследний отчёт о достижении:\n{goal.last_achievement_description}")

    if docx_content:
        parts.append(f"\n## Детальное описание цели (из DOCX):\n{docx_content}")

    return "\n".join(parts)


def _get_goal_or_raise(goals_map: GoalsMap, selected_goal_id: Optional[str]) -> GoalNodeV1:
    """
    Возвращает выбранную цель или выбрасывает ValueError.

    Args:
        goals_map: Карта целей.
        selected_goal_id: ID выбранной цели.

    Returns:
        GoalNodeV1: Объект цели.

    Raises:
        ValueError: Если цель не выбрана или не найдена.
    """
    if not selected_goal_id:
        raise ValueError("Для данного кейса необходимо выбрать цель из списка.")
    goal = get_goal_by_id(goals_map, selected_goal_id)
    if not goal:
        raise ValueError(f"Цель с ID {selected_goal_id} не найдена в карте целей.")
    return goal


async def run_case(
    case_id: int,
    goals_map: GoalsMap,
    selected_goal_id: Optional[str],
    docx_content: Optional[str],
) -> AsyncGenerator[str, None]:
    """
    Запускает один из 7 кейсов OKR-анализа и возвращает потоковый генератор.

    Args:
        case_id: Номер кейса (1-7).
        goals_map: Карта целей из Directum Targets.
        selected_goal_id: ID выбранной цели (для кейсов 1-4, 6).
        docx_content: Содержимое DOCX-файла.

    Returns:
        AsyncGenerator[str, None]: Потоковый генератор фрагментов ответа.

    Raises:
        ValueError: Если кейс не найден или цель не выбрана когда требуется.
    """
    handlers = {
        1: _case1_smart_check,
        2: _case2_key_results,
        3: _case3_quarterly_decomp,
        4: _case4_management_verify,
        5: _case5_conflicts,
        6: _case6_risks,
        7: _case7_express_report,
    }

    handler = handlers.get(case_id)
    if not handler:
        raise ValueError(f"Кейс {case_id} не существует. Допустимые кейсы: 1-7.")

    return handler(goals_map, selected_goal_id, docx_content)


def _case1_smart_check(
    goals_map: GoalsMap,
    selected_goal_id: Optional[str],
    docx_content: Optional[str],
) -> AsyncGenerator[str, None]:
    """
    Кейс 1: Анализ формулировки цели на соответствие SMART-критериям.

    Проверяет цель на конкретность, измеримость, достижимость,
    релевантность и ограниченность во времени. Генерирует улучшенные варианты.
    """
    goal = _get_goal_or_raise(goals_map, selected_goal_id)
    goal_ctx = _goal_context(goal, docx_content)
    map_text = format_map_for_llm(goals_map, selected_goal_id)

    messages = [
        {"role": "system", "content": SYSTEM_BASE},
        {"role": "user", "content": f"""Проанализируй формулировку цели на соответствие SMART-критериям и предложи улучшения.

{goal_ctx}

## Контекст карты целей:
{map_text}

## Твоя задача:
1. **SMART-анализ**: оцени каждый критерий (S - конкретность, M - измеримость, A - достижимость, R - релевантность, T - ограниченность во времени) — что выполнено, что нет.
2. **Амбициозность**: оцени, насколько цель амбициозна, но реалистична.
3. **2-3 улучшенных варианта формулировки** с объяснением, что изменилось.
4. **Краткие рекомендации** по улучшению.

Структурируй ответ с заголовками. Будь конкретным."""},
    ]

    return llm_service.stream_completion(messages)


def _case2_key_results(
    goals_map: GoalsMap,
    selected_goal_id: Optional[str],
    docx_content: Optional[str],
) -> AsyncGenerator[str, None]:
    """
    Кейс 2: Генерация и декомпозиция ключевых результатов для цели.

    Создаёт 3-4 варианта измеримых KR с учётом контекста карты целей.
    """
    goal = _get_goal_or_raise(goals_map, selected_goal_id)
    goal_ctx = _goal_context(goal, docx_content)

    messages = [
        {"role": "system", "content": SYSTEM_BASE},
        {"role": "user", "content": f"""Сформулируй ключевые результаты (KR) для цели согласно OKR-методологии.

{goal_ctx}

## Текущая ситуация:
- Цель уже имеет {goal.key_result_count} ключевых результатов (но нам нужны новые варианты)

## Твоя задача:
Предложи **3-4 варианта наборов ключевых результатов** для данной цели:

Для каждого набора:
- Укажи 2-4 конкретных, измеримых KR
- Каждый KR должен быть: конкретным числовым показателем, амбициозным но достижимым, измеримым к концу периода
- Объясни логику набора (на что он ориентирован)

Также дай рекомендации по выбору лучшего набора KR.

Структурируй ответ с заголовками для каждого варианта."""},
    ]

    return llm_service.stream_completion(messages)


def _case3_quarterly_decomp(
    goals_map: GoalsMap,
    selected_goal_id: Optional[str],
    docx_content: Optional[str],
) -> AsyncGenerator[str, None]:
    """
    Кейс 3: Декомпозиция годовой цели на квартальные подцели.

    Разбивает цель на квартальные этапы с учётом сезонности и зависимостей.
    """
    goal = _get_goal_or_raise(goals_map, selected_goal_id)
    goal_ctx = _goal_context(goal, docx_content)
    map_text = format_map_for_llm(goals_map, selected_goal_id)

    messages = [
        {"role": "system", "content": SYSTEM_BASE},
        {"role": "user", "content": f"""Выполни декомпозицию годовой цели на квартальные подцели.

{goal_ctx}

## Контекст карты целей (для понимания зависимостей):
{map_text}

## Твоя задача:
1. **Анализ текущего прогресса**: что уже сделано ({goal.progress:.0f}% выполнено), что остаётся.
2. **Квартальная декомпозиция** (Q1-Q4 или оставшиеся кварталы):
   - Для каждого квартала: конкретные подцели и ожидаемые результаты
   - Учти сезонность и логику нарастания прогресса
   - Укажи зависимости между кварталами
3. **KPI для каждого квартала**: как измерить успех квартала
4. **Риски разбивки**: что может помешать равномерному прогрессу

Структурируй как план с разделами по кварталам."""},
    ]

    return llm_service.stream_completion(messages)


def _case4_management_verify(
    goals_map: GoalsMap,
    selected_goal_id: Optional[str],
    docx_content: Optional[str],
) -> AsyncGenerator[str, None]:
    """
    Кейс 4: Верификация учёта ожиданий и замечаний руководства.

    Проверяет, насколько цель и её реализация соответствуют ожиданиям из DOCX.
    """
    goal = _get_goal_or_raise(goals_map, selected_goal_id)
    goal_ctx = _goal_context(goal, docx_content)

    if not docx_content:
        docx_note = "\n\n**Примечание:** DOCX-файл с описанием цели не загружен. Анализ будет ограничен данными из карты целей."
    else:
        docx_note = ""

    messages = [
        {"role": "system", "content": SYSTEM_BASE},
        {"role": "user", "content": f"""Проверь, насколько текущая реализация цели соответствует ожиданиям руководства.{docx_note}

{goal_ctx}

## Твоя задача:
1. **Чеклист ожиданий руководства**: выдели из описания (если есть) явные и неявные ожидания руководства.
2. **Анализ соответствия**: для каждого ожидания — выполнено ли оно, частично или нет.
3. **Выявленные расхождения**: что в текущей формулировке/реализации не соответствует ожиданиям.
4. **Рекомендации**: как скорректировать цель или план достижения для лучшего соответствия.

Структурируй как верификационный чеклист."""},
    ]

    return llm_service.stream_completion(messages)


def _case5_conflicts(
    goals_map: GoalsMap,
    selected_goal_id: Optional[str],
    docx_content: Optional[str],
) -> AsyncGenerator[str, None]:
    """
    Кейс 5: Выявление конфликтов и слепых зон в карте стратегических целей.

    Анализирует всю карту целей на наличие конфликтов приоритетов и пробелов в стратегии.
    """
    map_text = format_map_for_llm(goals_map)

    messages = [
        {"role": "system", "content": SYSTEM_BASE},
        {"role": "user", "content": f"""Проанализируй карту стратегических целей на конфликты, противоречия и слепые зоны.

## Карта целей:
{map_text}

## Твоя задача:
1. **Конфликты целей**: есть ли цели, которые противоречат друг другу (конкуренция за ресурсы, разные приоритеты, взаимоисключающие KR)?
2. **Слепые зоны**: какие важные стратегические направления не охвачены в карте?
3. **Дисбаланс приоритетов**: равномерно ли распределены усилия? Нет ли перегруза в одних областях при недостатке в других?
4. **Проблемы структуры**: есть ли цели без логической связи с верхним уровнем? Есть ли «висячие» цели?
5. **Рекомендации**: как устранить выявленные конфликты и закрыть слепые зоны?

Структурируй как аналитический отчёт с разделами."""},
    ]

    return llm_service.stream_completion(messages)


def _case6_risks(
    goals_map: GoalsMap,
    selected_goal_id: Optional[str],
    docx_content: Optional[str],
) -> AsyncGenerator[str, None]:
    """
    Кейс 6: Анализ рисков недостижения выбранной цели.

    Оценивает текущий прогресс и выявляет риски с рекомендациями по митигации.
    """
    goal = _get_goal_or_raise(goals_map, selected_goal_id)
    goal_ctx = _goal_context(goal, docx_content)
    map_text = format_map_for_llm(goals_map, selected_goal_id)

    messages = [
        {"role": "system", "content": SYSTEM_BASE},
        {"role": "user", "content": f"""Выполни анализ рисков недостижения цели на основе текущего прогресса и контекста.

{goal_ctx}

## Контекст карты целей:
{map_text}

## Твоя задача:
1. **Оценка текущего прогресса** ({goal.progress:.0f}%): на сколько реалистично достижение к концу периода?
2. **Матрица рисков** (минимум 4-5 рисков):
   - Название риска
   - Вероятность (Высокая/Средняя/Низкая)
   - Влияние (Высокое/Среднее/Низкое)
   - Описание
   - Способ митигации
3. **Критический путь**: какие зависимости и блокеры могут остановить прогресс?
4. **Рекомендуемые действия**: топ-3 действия для снижения рисков прямо сейчас.

Структурируй как риск-отчёт с таблицей рисков."""},
    ]

    return llm_service.stream_completion(messages)


def _case7_express_report(
    goals_map: GoalsMap,
    selected_goal_id: Optional[str],
    docx_content: Optional[str],
) -> AsyncGenerator[str, None]:
    """
    Кейс 7: Генерация экспресс-отчёта по целям с наибольшим отставанием.

    Анализирует всю карту и формирует топ-3 цели, требующие внимания.
    """
    map_text = format_map_for_llm(goals_map)

    messages = [
        {"role": "system", "content": SYSTEM_BASE},
        {"role": "user", "content": f"""Подготовь экспресс-отчёт по карте целей для руководства.

## Карта целей:
{map_text}

## Твоя задача:
1. **Топ-3 цели с наибольшим отставанием**:
   - Название и код цели
   - Текущий прогресс vs ожидаемый
   - Ключевые проблемы
   - Рекомендуемые действия

2. **Топ-3 цели в хорошем прогрессе** (для контраста и понимания best practices)

3. **Общая картина**: краткая сводка состояния портфеля целей (1-2 абзаца)

4. **Рекомендации для совещания**: на чём сосредоточить внимание руководства на следующей сессии?

Форматируй как управленческий отчёт: кратко, структурированно, по существу."""},
    ]

    return llm_service.stream_completion(messages)


# ============================================================
# V2 CASE METHODS (with context strings instead of GoalsMap)
# ============================================================

async def run_case_v2(
    case_id: int,
    map_context: str | None,
    target_context: str | None,
) -> AsyncGenerator[str, None]:
    """
    Запускает один из 7 кейсов OKR-анализа с использованием строковых контекстов (v2 API).

    Args:
        case_id: Номер кейса (1-7).
        map_context: Текстовый контекст карты целей (для кейсов 5, 7).
        target_context: Текстовый контекст выбранной цели (для кейсов 1-4, 6).

    Returns:
        AsyncGenerator[str, None]: Потоковый генератор фрагментов ответа.

    Raises:
        ValueError: Если кейс не найден или контекст не задан когда требуется.
    """
    handlers_v2 = {
        1: _case1_smart_check_v2,
        2: _case2_key_results_v2,
        3: _case3_quarterly_decomp_v2,
        4: _case4_management_verify_v2,
        5: _case5_conflicts_v2,
        6: _case6_risks_v2,
        7: _case7_express_report_v2,
    }

    handler = handlers_v2.get(case_id)
    if not handler:
        raise ValueError(f"Кейс {case_id} не существует. Допустимые кейсы: 1-7.")

    return handler(map_context, target_context)


def _case1_smart_check_v2(
    map_context: str | None,
    target_context: str | None,
) -> AsyncGenerator[str, None]:
    """Кейс 1 v2: Анализ формулировки цели на соответствие SMART-критериям."""
    if not target_context:
        raise ValueError("Для кейса 1 необходимо выбрать цель.")

    messages = [
        {"role": "system", "content": SYSTEM_BASE},
        {"role": "user", "content": f"""Проанализируй формулировку цели на соответствие SMART-критериям и предложи улучшения.

{target_context}

## Твоя задача:
1. **SMART-анализ**: оцени каждый критерий (S - конкретность, M - измеримость, A - достижимость, R - релевантность, T - ограниченность во времени) — что выполнено, что нет.
2. **Амбициозность**: оцени, насколько цель амбициозна, но реалистична.
3. **2-3 улучшенных варианта формулировки** с объяснением, что изменилось.
4. **Краткие рекомендации** по улучшению.

Структурируй ответ с заголовками. Будь конкретным."""},
    ]

    return llm_service.stream_completion(messages)


def _case2_key_results_v2(
    map_context: str | None,
    target_context: str | None,
) -> AsyncGenerator[str, None]:
    """Кейс 2 v2: Генерация и декомпозиция ключевых результатов для цели."""
    if not target_context:
        raise ValueError("Для кейса 2 необходимо выбрать цель.")

    messages = [
        {"role": "system", "content": SYSTEM_BASE},
        {"role": "user", "content": f"""Сформулируй ключевые результаты (KR) для цели согласно OKR-методологии.

{target_context}

## Твоя задача:
Предложи **3-4 варианта наборов ключевых результатов** для данной цели:

Для каждого набора:
- Укажи 2-4 конкретных, измеримых KR
- Каждый KR должен быть: конкретным числовым показателем, амбициозным но достижимым, измеримым к концу периода
- Объясни логику набора (на что он ориентирован)

Также дай рекомендации по выбору лучшего набора KR.

Структурируй ответ с заголовками для каждого варианта."""},
    ]

    return llm_service.stream_completion(messages)


def _case3_quarterly_decomp_v2(
    map_context: str | None,
    target_context: str | None,
) -> AsyncGenerator[str, None]:
    """Кейс 3 v2: Декомпозиция годовой цели на квартальные подцели."""
    if not target_context:
        raise ValueError("Для кейса 3 необходимо выбрать цель.")

    messages = [
        {"role": "system", "content": SYSTEM_BASE},
        {"role": "user", "content": f"""Выполни декомпозицию годовой цели на квартальные подцели.

{target_context}

## Твоя задача:
1. **Анализ текущего прогресса**: что уже сделано, что остаётся.
2. **Квартальная декомпозиция** (Q1-Q4 или оставшиеся кварталы):
   - Для каждого квартала: конкретные подцели и ожидаемые результаты
   - Учти сезонность и логику нарастания прогресса
   - Укажи зависимости между кварталами
3. **KPI для каждого квартала**: как измерить успех квартала
4. **Риски разбивки**: что может помешать равномерному прогрессу

Структурируй как план с разделами по кварталам."""},
    ]

    return llm_service.stream_completion(messages)


def _case4_management_verify_v2(
    map_context: str | None,
    target_context: str | None,
) -> AsyncGenerator[str, None]:
    """Кейс 4 v2: Верификация учёта ожиданий и замечаний руководства."""
    if not target_context:
        raise ValueError("Для кейса 4 необходимо выбрать цель.")

    messages = [
        {"role": "system", "content": SYSTEM_BASE},
        {"role": "user", "content": f"""Проверь, насколько текущая реализация цели соответствует ожиданиям руководства.

{target_context}

## Твоя задача:
1. **Чеклист ожиданий руководства**: выдели из описания (если есть) явные и неявные ожидания руководства.
2. **Анализ соответствия**: для каждого ожидания — выполнено ли оно, частично или нет.
3. **Выявленные расхождения**: что в текущей формулировке/реализации не соответствует ожиданиям.
4. **Рекомендации**: как скорректировать цель или план достижения для лучшего соответствия.

Структурируй как верификационный чеклист."""},
    ]

    return llm_service.stream_completion(messages)


def _case5_conflicts_v2(
    map_context: str | None,
    target_context: str | None,
) -> AsyncGenerator[str, None]:
    """Кейс 5 v2: Выявление конфликтов и слепых зон в карте стратегических целей."""
    if not map_context:
        raise ValueError("Для кейса 5 необходимо выбрать карту целей.")

    messages = [
        {"role": "system", "content": SYSTEM_BASE},
        {"role": "user", "content": f"""Проанализируй карту стратегических целей на конфликты, противоречия и слепые зоны.

## Карта целей:
{map_context}

## Твоя задача:
1. **Конфликты целей**: есть ли цели, которые противоречат друг другу (конкуренция за ресурсы, разные приоритеты, взаимоисключающие KR)?
2. **Слепые зоны**: какие важные стратегические направления не охвачены в карте?
3. **Дисбаланс приоритетов**: равномерно ли распределены усилия? Нет ли перегруза в одних областях при недостатке в других?
4. **Проблемы структуры**: есть ли цели без логической связи с верхним уровнем? Есть ли «висячие» цели?
5. **Рекомендации**: как устранить выявленные конфликты и закрыть слепые зоны?

Структурируй как аналитический отчёт с разделами."""},
    ]

    return llm_service.stream_completion(messages)


def _case6_risks_v2(
    map_context: str | None,
    target_context: str | None,
) -> AsyncGenerator[str, None]:
    """Кейс 6 v2: Анализ рисков недостижения выбранной цели."""
    if not target_context:
        raise ValueError("Для кейса 6 необходимо выбрать цель.")

    messages = [
        {"role": "system", "content": SYSTEM_BASE},
        {"role": "user", "content": f"""Выполни анализ рисков недостижения цели на основе текущего прогресса и контекста.

{target_context}

## Твоя задача:
1. **Оценка текущего прогресса**: на сколько реалистично достижение к концу периода?
2. **Матрица рисков** (минимум 4-5 рисков):
   - Название риска
   - Вероятность (Высокая/Средняя/Низкая)
   - Влияние (Высокое/Среднее/Низкое)
   - Описание
   - Способ митигации
3. **Критический путь**: какие зависимости и блокеры могут остановить прогресс?
4. **Рекомендуемые действия**: топ-3 действия для снижения рисков прямо сейчас.

Структурируй как риск-отчёт с таблицей рисков."""},
    ]

    return llm_service.stream_completion(messages)


def _case7_express_report_v2(
    map_context: str | None,
    target_context: str | None,
) -> AsyncGenerator[str, None]:
    """Кейс 7 v2: Генерация экспресс-отчёта по целям с наибольшим отставанием."""
    if not map_context:
        raise ValueError("Для кейса 7 необходимо выбрать карту целей.")

    messages = [
        {"role": "system", "content": SYSTEM_BASE},
        {"role": "user", "content": f"""Подготовь экспресс-отчёт по карте целей для руководства.

## Карта целей:
{map_context}

## Твоя задача:
1. **Топ-3 цели с наибольшим отставанием**:
   - Название и код цели
   - Текущий прогресс vs ожидаемый
   - Ключевые проблемы
   - Рекомендуемые действия

2. **Топ-3 цели в хорошем прогрессе** (для контраста и понимания best practices)

3. **Общая картина**: краткая сводка состояния портфеля целей (1-2 абзаца)

4. **Рекомендации для совещания**: на чём сосредоточить внимание руководства на следующей сессии?

Форматируй как управленческий отчёт: кратко, структурированно, по существу."""},
    ]

    return llm_service.stream_completion(messages)
