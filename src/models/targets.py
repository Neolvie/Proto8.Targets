"""Pydantic-модели для карты целей Directum Targets."""

from typing import Optional
from pydantic import BaseModel, Field


class GoalNode(BaseModel):
    """Узел карты целей (одна цель из Directum Targets)."""

    id: str = Field(description="Строковый идентификатор цели")
    target_id: int = Field(description="Числовой ID цели")
    code: str = Field(description="Код цели (например U-26.4.2)")
    name: str = Field(description="Название цели")
    parent_id: Optional[str] = Field(default=None, description="ID родительской цели")
    child_ids: list[str] = Field(default_factory=list, description="Список ID дочерних целей")
    priority: str = Field(default="", description="Приоритет: High/Medium/Low")
    progress: float = Field(default=0.0, description="Прогресс достижения в процентах (0-100)")
    status_name: str = Field(default="", description="Название статуса")
    status_state: str = Field(default="", description="Состояние статуса")
    status_icon: Optional[str] = Field(default=None, description="Иконка статуса")
    responsible_name: str = Field(default="", description="ФИО ответственного")
    structural_unit: str = Field(default="", description="Структурное подразделение")
    period_name: str = Field(default="", description="Период (например: I квартал 2026)")
    period_timeframe: str = Field(default="", description="Тип периода: Year/Quarter/Month")
    key_result_count: int = Field(default=0, description="Количество ключевых результатов")
    last_achievement_description: Optional[str] = Field(default=None, description="Описание последнего статуса достижения")


class GoalsMap(BaseModel):
    """Карта целей из Directum Targets."""

    nodes: list[GoalNode] = Field(description="Список всех узлов-целей")
    map_name: str = Field(default="", description="Название карты целей")
    map_id: Optional[int] = Field(default=None, description="ID карты")
    total_progress: float = Field(default=0.0, description="Общий прогресс карты")
