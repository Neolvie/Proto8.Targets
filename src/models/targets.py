"""Pydantic-модели для Directum Targets API v2."""

from typing import Optional, List, Any
from pydantic import BaseModel, Field


# ============================================================
# Модели для API endpoint'ов (v2)
# ============================================================

class TargetsMap(BaseModel):
    """Карта целей из списка карт (ITargetsTargetsMaps)."""

    Id: int
    Name: str
    Code: str
    PeriodLabel: str
    AchievementPercentage: float = 0.0
    Status: str = "Unknown"
    Notes: Optional[str] = None
    PeriodStart: Optional[str] = None
    PeriodEnd: Optional[str] = None

    class Config:
        extra = "ignore"  # Игнорировать лишние поля


class ResponsiblePerson(BaseModel):
    """Ответственное лицо."""

    Id: int
    Name: str
    TypeGuid: Optional[str] = None

    class Config:
        extra = "ignore"


class StructuralUnitInfo(BaseModel):
    """Структурное подразделение."""

    Id: int
    Name: str
    TypeGuid: Optional[str] = None

    class Config:
        extra = "ignore"


class PeriodInfo(BaseModel):
    """Информация о периоде."""

    Name: str
    Code: Optional[str] = None
    TimeFrame: Optional[str] = None
    StartDate: Optional[str] = None

    class Config:
        extra = "ignore"


class AchievementStatus(BaseModel):
    """Статус достижения."""

    Id: int = 0
    Name: Optional[str] = None
    Color: Optional[str] = None
    TypeGuid: Optional[str] = None
    IsApproved: bool = False

    class Config:
        extra = "ignore"


class LastAchievementStatus(BaseModel):
    """Последний отчёт о статусе достижения."""

    Id: int = 0
    Description: Optional[str] = None
    ReportDate: Optional[str] = None
    CanAdd: bool = False
    CanChange: bool = False
    AchievementStatus: Optional[AchievementStatus] = None

    class Config:
        extra = "ignore"


class GoalStatus(BaseModel):
    """Статус цели."""

    State: str = ""
    Name: str = ""
    Icon: Optional[str] = None
    LastAchievementStatus: Optional[Any] = None

    class Config:
        extra = "ignore"


class GoalNode(BaseModel):
    """Узел карты целей (из GetGoalsMap)."""

    TargetId: int
    Code: str
    Name: str
    ParentId: Optional[str] = None
    ChildIds: List[Any] = Field(default_factory=list)
    Priority: str = "Medium"
    Progress: float = 0.0
    KeyResultCount: int = 0
    Status: Optional[GoalStatus] = None
    Responsible: Optional[ResponsiblePerson] = None
    StructuralUnit: Optional[StructuralUnitInfo] = None
    Period: Optional[PeriodInfo] = None

    # Дополнительные поля, которые могут присутствовать
    Id: Optional[str] = None
    MapId: Optional[int] = None
    ParentRelationType: Optional[str] = None
    LinksCount: Optional[int] = None

    class Config:
        extra = "ignore"


class MapInfo(BaseModel):
    """Информация о карте (из GetGoalsMap)."""

    Id: int
    Name: str
    Progress: float = 0.0
    TypeGuid: Optional[str] = None
    IsReadOnly: Optional[bool] = None

    class Config:
        extra = "ignore"


class MapGraphPayload(BaseModel):
    """Payload графа карты."""

    Nodes: List[GoalNode]
    Map: MapInfo

    class Config:
        extra = "ignore"


class MapGraph(BaseModel):
    """Граф целей карты (ответ GetGoalsMap)."""

    IsSuccess: bool = True
    Message: Optional[str] = None
    Payload: MapGraphPayload

    class Config:
        extra = "ignore"


class TargetDetail(BaseModel):
    """Расширенная информация по цели (ITargetsTargets)."""

    Id: int
    Name: str
    Code: str
    StatusDescription: str = ""
    PeriodLabel: str = ""
    AchievementPercentage: float = 0.0
    PeriodStart: Optional[str] = None
    PeriodEnd: Optional[str] = None
    IsPersonal: bool = False
    Description: Optional[str] = None
    Notes: Optional[str] = None
    Priority: str = "Medium"

    # Дополнительные поля
    KeyResultsByMetrics: Optional[bool] = None
    CodeIndex: Optional[int] = None
    PeriodData: Optional[str] = None
    Status: Optional[str] = None

    class Config:
        extra = "ignore"


class KeyResult(BaseModel):
    """Ключевой результат (из GetKeyResults)."""

    Description: str
    AchievementPercentage: str = "0"
    Metric: Optional[str] = None
    InitialValue: Optional[str] = None
    PlannedValue: Optional[str] = None
    ActualValue: Optional[str] = None
    ExtensionPoint: Optional[Any] = None

    class Config:
        extra = "ignore"


# ============================================================
# Модели для обратной совместимости с v1 (сохраняем для парсеров)
# ============================================================

class GoalNodeV1(BaseModel):
    """Узел карты целей (v1 совместимость)."""

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
    """Карта целей (v1 совместимость)."""

    nodes: list[GoalNodeV1] = Field(description="Список всех узлов-целей")
    map_name: str = Field(default="", description="Название карты целей")
    map_id: Optional[int] = Field(default=None, description="ID карты")
    total_progress: float = Field(default=0.0, description="Общий прогресс карты")
