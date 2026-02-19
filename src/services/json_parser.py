"""Парсер JSON-карты целей из Directum Targets API."""

import json
from typing import Any
from src.models.targets import GoalNodeV1, GoalsMap


def parse_goals_map(json_text: str) -> GoalsMap:
    """
    Парсит JSON-текст карты целей Directum Targets в объект GoalsMap.

    Поддерживает формат ответа API:
    /odata/Sungero.IntegrationService.Models.Generated.Targets.IGetGoalsMap

    Args:
        json_text: Строка с JSON-содержимым карты целей.

    Returns:
        GoalsMap: Объект с разобранными целями.

    Raises:
        ValueError: Если JSON невалиден или структура не соответствует формату Targets.
    """
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Невалидный JSON: {e}") from e

    if not isinstance(data, dict):
        raise ValueError("JSON должен быть объектом (словарём)")

    # Поддержка формата с Payload или без
    payload = data.get("Payload", data)

    nodes_raw = payload.get("Nodes")
    if nodes_raw is None:
        raise ValueError("Не найдено поле 'Nodes' в карте целей")
    if not isinstance(nodes_raw, list):
        raise ValueError("Поле 'Nodes' должно быть массивом")

    nodes = []
    for raw in nodes_raw:
        node = _parse_node(raw)
        nodes.append(node)

    # Данные карты
    map_data = payload.get("Map", {})
    map_name = map_data.get("Name", "") if map_data else ""
    map_id = map_data.get("Id") if map_data else None
    total_progress = map_data.get("Progress", 0.0) if map_data else 0.0

    return GoalsMap(
        nodes=nodes,
        map_name=map_name,
        map_id=map_id,
        total_progress=total_progress,
    )


def _parse_node(raw: dict[str, Any]) -> GoalNodeV1:
    """
    Разбирает один узел карты целей из сырого словаря.

    Args:
        raw: Словарь с данными одного узла.

    Returns:
        GoalNodeV1: Объект узла карты целей (v1 совместимость).
    """
    status = raw.get("Status", {}) or {}
    last_achievement = status.get("LastAchievementStatus", {}) or {}
    achievement_desc = last_achievement.get("Description") if last_achievement else None

    responsible = raw.get("Responsible", {}) or {}
    structural_unit = raw.get("StructuralUnit", {}) or {}
    period = raw.get("Period", {}) or {}

    # ParentId может быть строкой "114" или числом или null
    parent_id = raw.get("ParentId")
    if parent_id is not None:
        parent_id = str(parent_id)

    child_ids = [str(c) for c in (raw.get("ChildIds") or [])]

    return GoalNodeV1(
        id=str(raw.get("Id", "")),
        target_id=int(raw.get("TargetId", 0)),
        code=raw.get("Code", ""),
        name=raw.get("Name", ""),
        parent_id=parent_id,
        child_ids=child_ids,
        priority=raw.get("Priority", ""),
        progress=float(raw.get("Progress", 0.0)),
        status_name=status.get("Name", ""),
        status_state=status.get("State", ""),
        status_icon=status.get("Icon"),
        responsible_name=responsible.get("Name", ""),
        structural_unit=structural_unit.get("Name", ""),
        period_name=period.get("Name", ""),
        period_timeframe=period.get("TimeFrame", ""),
        key_result_count=int(raw.get("KeyResultCount", 0)),
        last_achievement_description=achievement_desc,
    )


def format_map_for_llm(goals_map: GoalsMap, selected_goal_id: str | None = None) -> str:
    """
    Форматирует карту целей в текст для передачи в LLM.

    Args:
        goals_map: Объект карты целей.
        selected_goal_id: Если задан — выбранная цель выделяется в тексте.

    Returns:
        str: Текстовое представление карты целей.
    """
    lines = [
        f"# Карта целей: {goals_map.map_name}",
        f"Общий прогресс: {goals_map.total_progress:.1f}%",
        f"Всего целей: {len(goals_map.nodes)}",
        "",
    ]

    # Определяем корневые цели (без родителей)
    root_nodes = [n for n in goals_map.nodes if n.parent_id is None]
    node_map = {n.id: n for n in goals_map.nodes}

    def format_node(node: GoalNodeV1, indent: int = 0) -> None:
        prefix = "  " * indent + ("- " if indent > 0 else "")
        marker = " [ВЫБРАННАЯ ЦЕЛЬ]" if node.id == selected_goal_id else ""
        lines.append(f"{prefix}**{node.code}**: {node.name}{marker}")
        lines.append(f"  {'  ' * indent}Прогресс: {node.progress:.0f}% | Статус: {node.status_name} | Приоритет: {node.priority}")
        lines.append(f"  {'  ' * indent}Ответственный: {node.responsible_name} | Период: {node.period_name}")
        if node.last_achievement_description:
            desc = node.last_achievement_description[:300]
            if len(node.last_achievement_description) > 300:
                desc += "..."
            lines.append(f"  {'  ' * indent}Последний статус: {desc}")
        lines.append("")

        # Дочерние цели
        for child_id in node.child_ids:
            if child_id in node_map:
                format_node(node_map[child_id], indent + 1)

    if root_nodes:
        for root in root_nodes:
            format_node(root)
    else:
        # Если нет корневых — выводим все подряд
        for node in goals_map.nodes:
            format_node(node)

    return "\n".join(lines)


def get_goal_by_id(goals_map: GoalsMap, goal_id: str) -> GoalNodeV1 | None:
    """
    Возвращает узел цели по её ID.

    Args:
        goals_map: Карта целей.
        goal_id: ID искомой цели.

    Returns:
        GoalNodeV1 или None если цель не найдена.
    """
    for node in goals_map.nodes:
        if node.id == goal_id:
            return node
    return None
