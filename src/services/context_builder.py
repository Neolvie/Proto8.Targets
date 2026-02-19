"""Формирование компактного текстового контекста для передачи в LLM."""

from typing import List
import tiktoken

from src.models.targets import GoalNode, TargetsMap, TargetDetail, KeyResult


def normalize_text(text: str | None) -> str:
    """
    Удаляет escape-последовательности из текстовых полей.

    Args:
        text: Исходный текст с возможными escape-последовательностями.

    Returns:
        str: Нормализованный текст.

    Примеры:
        - \\n → \n (реальный перенос)
        - \\\\ → \\ (одинарный слеш)
        - \\r → (удалить)
    """
    if not text:
        return ""

    # Замена escape-последовательностей
    result = text
    result = result.replace("\\n", "\n")
    result = result.replace("\\\\", "\\")
    result = result.replace("\\r", "")

    return result


def build_map_context(nodes: List[GoalNode], map_info: TargetsMap) -> str:
    """
    Формирует компактный текстовый контекст карты целей.

    Args:
        nodes: Список узлов целей из MapGraph.
        map_info: Информация о карте целей.

    Returns:
        str: Компактный текстовый контекст в формате FR-16.

    Формат:
        Карта целей: {Name} | Период: {PeriodLabel} | Прогресс: {AchievementPercentage}%

        [{Code}] {Name}
          Ответственный: {Responsible.Name} | Подразделение: {StructuralUnit.Name}
          Период: {Period.Name} | Приоритет: {Priority} | Прогресс: {Progress}% | КР: {KeyResultCount}
          Статус: {Status.Name} {Status.Icon}
          Дочерние: {ChildIds -> Code, Name}
          Отчёт ({ReportDate}): {LastAchievementStatus.Description}
        ---
    """
    lines = []
    lines.append(
        f"Карта целей: {map_info.Name} | Период: {map_info.PeriodLabel} | "
        f"Прогресс: {map_info.AchievementPercentage}%\n"
    )

    # Создаём словарь для быстрого поиска целей по ID
    nodes_by_id = {str(node.TargetId): node for node in nodes}

    for node in nodes:
        lines.append(f"[{node.Code}] {node.Name}")

        # Ответственный и подразделение
        responsible = node.Responsible.Name if node.Responsible else "—"
        unit = node.StructuralUnit.Name if node.StructuralUnit else "—"
        lines.append(f"  Ответственный: {responsible} | Подразделение: {unit}")

        # Период, приоритет, прогресс, КР
        period = node.Period.Name if node.Period else "—"
        lines.append(
            f"  Период: {period} | Приоритет: {node.Priority} | "
            f"Прогресс: {node.Progress}% | КР: {node.KeyResultCount}"
        )

        # Статус
        status_name = node.Status.Name if node.Status else "—"
        status_icon = f" {node.Status.Icon}" if node.Status and node.Status.Icon else ""
        lines.append(f"  Статус: {status_name}{status_icon}")

        # Дочерние цели
        if node.ChildIds:
            child_codes = []
            for child_id in node.ChildIds:
                child_node = nodes_by_id.get(str(child_id))
                if child_node:
                    child_codes.append(f"{child_node.Code}")
            child_str = ", ".join(child_codes) if child_codes else "—"
        else:
            child_str = "—"
        lines.append(f"  Дочерние: {child_str}")

        # Последний отчёт (LastAchievementStatus может быть dict или объектом)
        las = node.Status.LastAchievementStatus if node.Status else None
        if las:
            if isinstance(las, dict):
                description = las.get("Description") or ""
                report_date = las.get("ReportDate") or "—"
            else:
                description = getattr(las, "Description", None) or ""
                report_date = getattr(las, "ReportDate", None) or "—"
            if description:
                description = normalize_text(description)
                if len(description) > 500:
                    description = description[:500] + "..."
                lines.append(f"  Отчёт ({report_date}): {description}")

        lines.append("---\n")

    return "\n".join(lines)


def build_target_context(target: TargetDetail, key_results: List[KeyResult]) -> str:
    """
    Формирует компактный текстовый контекст цели.

    Args:
        target: Расширенная информация по цели.
        key_results: Список ключевых результатов.

    Returns:
        str: Компактный текстовый контекст в формате FR-17.

    Формат:
        Цель: [{Code}] {Name}
        Период: {PeriodLabel} ({PeriodStart} — {PeriodEnd})
        Статус: {StatusDescription} | Прогресс: {AchievementPercentage}% | Приоритет: {Priority}

        Описание:
        {Description}

        Заметки руководства:
        {Notes}

        Ключевые результаты:
        - {Description}: {AchievementPercentage}%
          (Метрика: {Metric} | Нач: {InitialValue} | План: {PlannedValue} | Факт: {ActualValue})
    """
    lines = []

    # Заголовок цели
    lines.append(f"Цель: [{target.Code}] {target.Name}")
    lines.append(
        f"Период: {target.PeriodLabel} ({target.PeriodStart} — {target.PeriodEnd})"
    )
    lines.append(
        f"Статус: {target.StatusDescription} | Прогресс: {target.AchievementPercentage}% | "
        f"Приоритет: {target.Priority}\n"
    )

    # Описание
    if target.Description:
        description = normalize_text(target.Description)
        lines.append("Описание:")
        lines.append(description)
        lines.append("")

    # Заметки руководства
    if target.Notes:
        notes = normalize_text(target.Notes)
        lines.append("Заметки руководства:")
        lines.append(notes)
        lines.append("")

    # Ключевые результаты
    if key_results:
        lines.append("Ключевые результаты:")
        for kr in key_results:
            metric_str = kr.Metric or "—"
            initial_str = kr.InitialValue or "—"
            planned_str = kr.PlannedValue or "—"
            actual_str = kr.ActualValue or "—"

            lines.append(
                f"- {kr.Description}: {kr.AchievementPercentage}%"
            )
            lines.append(
                f"  (Метрика: {metric_str} | Нач: {initial_str} | План: {planned_str} | Факт: {actual_str})"
            )

    return "\n".join(lines)


def estimate_tokens(text: str, model: str = "gpt-4o") -> int:
    """
    Оценивает количество токенов в тексте через tiktoken.

    Args:
        text: Текст для оценки.
        model: Название модели (по умолчанию gpt-4o).

    Returns:
        int: Примерное количество токенов.

    Используется для проверки размера контекста перед передачей в модель.
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback на cl100k_base для неизвестных моделей
        encoding = tiktoken.get_encoding("cl100k_base")

    return len(encoding.encode(text))
