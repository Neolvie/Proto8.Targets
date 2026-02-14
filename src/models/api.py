"""Pydantic-модели для запросов и ответов API."""

from typing import Optional, Literal
from pydantic import BaseModel, Field
from src.models.targets import GoalsMap


class CaseRequest(BaseModel):
    """Запрос на выполнение одного из 7 кейсов OKR-анализа."""

    goals_map: GoalsMap = Field(description="Карта целей из Directum Targets")
    selected_goal_id: Optional[str] = Field(
        default=None,
        description="ID выбранной цели (обязателен для кейсов 1-4, 6; None для кейсов 5, 7)"
    )
    docx_content: Optional[str] = Field(
        default=None,
        description="Текстовое содержимое DOCX-файла описания цели"
    )


class ChatMessage(BaseModel):
    """Одно сообщение в истории чата."""

    role: Literal["user", "assistant", "system"] = Field(description="Роль отправителя")
    content: str = Field(description="Текст сообщения")


class ChatRequest(BaseModel):
    """Запрос к свободному чату с ИИ-помощником."""

    goals_map: GoalsMap = Field(description="Карта целей из Directum Targets")
    docx_content: Optional[str] = Field(
        default=None,
        description="Текстовое содержимое DOCX-файла"
    )
    messages: list[ChatMessage] = Field(
        default_factory=list,
        description="История сообщений текущей сессии"
    )


class FeedbackRequest(BaseModel):
    """Запрос на сохранение оценки (👍/👎) результата кейса."""

    case_id: int = Field(ge=1, le=7, description="ID кейса (1-7)")
    session_id: str = Field(description="Уникальный идентификатор сессии браузера")
    vote: Literal[1, -1] = Field(description="Оценка: 1 — положительная 👍, -1 — отрицательная 👎")


class JsonUploadRequest(BaseModel):
    """Запрос на загрузку JSON-карты целей в виде текста."""

    json_text: str = Field(description="Текст JSON-файла карты целей")


class GoalListItem(BaseModel):
    """Элемент списка целей для выпадающего меню."""

    id: str
    code: str
    name: str
    priority: str
    progress: float
    period_name: str
    status_name: str


class DataLoadResponse(BaseModel):
    """Ответ на загрузку данных (JSON + DOCX)."""

    goals_map: GoalsMap
    docx_content: Optional[str]
    goals_list: list[GoalListItem]
    map_summary: str
