"""Главный модуль FastAPI приложения ИИ-помощника для Directum Targets."""

import os
import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_data_dir
from src.models.api import (
    CaseRequest, ChatRequest, FeedbackRequest,
    DataLoadResponse, GoalListItem, JsonUploadRequest,
)
from src.services.json_parser import parse_goals_map, format_map_for_llm
from src.services.docx_parser import parse_docx_bytes, parse_docx_file
from src.services import cases_service, chat_service
from src.services.metrics_storage import init_db, log_request, save_feedback, get_metrics

# Инициализация базы данных при запуске
init_db()

app = FastAPI(
    title="Directum Targets AI Assistant",
    description="ИИ-помощник для работы с целями и KR из Directum Targets",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Раздача статических файлов
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


def _get_client_ip(request: Request) -> str:
    """
    Извлекает IP-адрес клиента из заголовков запроса.

    Args:
        request: Объект входящего запроса FastAPI.

    Returns:
        str: IP-адрес клиента.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _goals_to_list(goals_map) -> list[GoalListItem]:
    """
    Преобразует карту целей в список элементов для выпадающего меню.

    Args:
        goals_map: Объект GoalsMap с узлами целей.

    Returns:
        list[GoalListItem]: Список элементов для dropdown в UI.
    """
    return [
        GoalListItem(
            id=node.id,
            code=node.code,
            name=node.name,
            priority=node.priority,
            progress=node.progress,
            period_name=node.period_name,
            status_name=node.status_name,
        )
        for node in goals_map.nodes
    ]


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Главная страница приложения."""
    index_path = static_dir / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html не найден")
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"))


@app.get("/backoffice", response_class=HTMLResponse)
async def backoffice(request: Request):
    """Страница метрик бэк-офиса."""
    backoffice_path = static_dir / "backoffice.html"
    if not backoffice_path.exists():
        raise HTTPException(status_code=404, detail="backoffice.html не найден")
    return HTMLResponse(content=backoffice_path.read_text(encoding="utf-8"))


@app.get("/api/health")
async def health():
    """Healthcheck endpoint."""
    return {"status": "ok", "service": "Directum Targets AI Assistant"}


@app.get("/api/data/test")
async def load_test_data(request: Request):
    """
    Загружает тестовые данные (Ario.json + Ario.docx) из папки /data.

    Returns:
        DataLoadResponse: Объект с картой целей, содержимым DOCX и списком целей.

    Raises:
        HTTPException: Если тестовые файлы не найдены.
    """
    data_dir = get_data_dir()
    json_path = os.path.join(data_dir, "Ario.json")
    docx_path = os.path.join(data_dir, "Ario.docx")

    if not os.path.exists(json_path):
        raise HTTPException(
            status_code=404,
            detail=f"Тестовый файл Ario.json не найден в {data_dir}"
        )

    with open(json_path, "r", encoding="utf-8") as f:
        json_text = f.read()

    try:
        goals_map = parse_goals_map(json_text)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    docx_content = None
    if os.path.exists(docx_path):
        try:
            docx_content = parse_docx_file(docx_path)
        except Exception:
            docx_content = None  # DOCX не критичен

    ip = _get_client_ip(request)
    log_request(ip, "/api/data/test")

    return DataLoadResponse(
        goals_map=goals_map,
        docx_content=docx_content,
        goals_list=_goals_to_list(goals_map),
        map_summary=f"Карта: {goals_map.map_name} | Целей: {len(goals_map.nodes)} | Прогресс: {goals_map.total_progress:.1f}%",
    )


@app.post("/api/data/upload")
async def upload_data(
    request: Request,
    json_file: Optional[UploadFile] = File(default=None),
    docx_file: Optional[UploadFile] = File(default=None),
    json_text: Optional[str] = Form(default=None),
):
    """
    Загружает пользовательские файлы: JSON-карту целей и/или DOCX-описание.

    Принимает JSON как файл или как текст в форм-данных.

    Returns:
        DataLoadResponse: Объект с картой целей, содержимым DOCX и списком целей.

    Raises:
        HTTPException: Если данные не предоставлены или невалидны.
    """
    # Получаем JSON
    raw_json_text = None
    if json_file and json_file.filename:
        content = await json_file.read()
        raw_json_text = content.decode("utf-8")
    elif json_text:
        raw_json_text = json_text

    if not raw_json_text:
        raise HTTPException(status_code=422, detail="Необходимо предоставить JSON-файл или текст карты целей")

    try:
        goals_map = parse_goals_map(raw_json_text)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Получаем DOCX если предоставлен
    docx_content = None
    if docx_file and docx_file.filename:
        docx_bytes = await docx_file.read()
        try:
            docx_content = parse_docx_bytes(docx_bytes)
        except ValueError:
            docx_content = None  # Не прерываем загрузку если DOCX невалиден

    ip = _get_client_ip(request)
    log_request(ip, "/api/data/upload")

    return DataLoadResponse(
        goals_map=goals_map,
        docx_content=docx_content,
        goals_list=_goals_to_list(goals_map),
        map_summary=f"Карта: {goals_map.map_name} | Целей: {len(goals_map.nodes)} | Прогресс: {goals_map.total_progress:.1f}%",
    )


@app.post("/api/cases/{case_id}")
async def run_case(case_id: int, request: Request, body: CaseRequest):
    """
    Запускает один из 7 кейсов OKR-анализа с потоковым ответом (SSE).

    Args:
        case_id: Номер кейса (1-7).
        body: Данные запроса с картой целей и ID выбранной цели.

    Returns:
        StreamingResponse: Поток текстовых фрагментов в формате SSE.

    Raises:
        HTTPException: Если кейс не найден или цель не выбрана.
    """
    if case_id < 1 or case_id > 7:
        raise HTTPException(status_code=400, detail="Номер кейса должен быть от 1 до 7")

    ip = _get_client_ip(request)
    log_request(ip, f"/api/cases/{case_id}", case_id=case_id)

    try:
        generator = await cases_service.run_case(
            case_id=case_id,
            goals_map=body.goals_map,
            selected_goal_id=body.selected_goal_id,
            docx_content=body.docx_content,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    async def sse_stream():
        """Генератор SSE-событий для потоковой передачи ответа."""
        try:
            async for chunk in generator:
                # Экранируем newlines в SSE формате
                for line in chunk.split("\n"):
                    yield f"data: {json.dumps(line)}\n\n"
        except ValueError as e:
            yield f"data: {json.dumps('[ERROR] ' + str(e))}\n\n"
        except RuntimeError as e:
            yield f"data: {json.dumps('[ERROR] ' + str(e))}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        sse_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@app.post("/api/chat")
async def chat(request: Request, body: ChatRequest):
    """
    Выполняет запрос к свободному чату с ИИ-помощником с потоковым ответом (SSE).

    Args:
        body: Данные запроса с картой целей, историей сообщений и содержимым DOCX.

    Returns:
        StreamingResponse: Поток текстовых фрагментов в формате SSE.
    """
    ip = _get_client_ip(request)
    log_request(ip, "/api/chat")

    try:
        generator = await chat_service.run_chat(
            goals_map=body.goals_map,
            messages=body.messages,
            docx_content=body.docx_content,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    async def sse_stream():
        """Генератор SSE-событий для потоковой передачи ответа чата."""
        try:
            async for chunk in generator:
                for line in chunk.split("\n"):
                    yield f"data: {json.dumps(line)}\n\n"
        except ValueError as e:
            yield f"data: {json.dumps('[ERROR] ' + str(e))}\n\n"
        except RuntimeError as e:
            yield f"data: {json.dumps('[ERROR] ' + str(e))}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        sse_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@app.post("/api/feedback")
async def feedback(request: Request, body: FeedbackRequest):
    """
    Сохраняет оценку пользователя (👍/👎) для результата кейса.

    Args:
        body: Данные оценки: ID кейса, сессии и vote (1/-1).

    Returns:
        dict: Подтверждение сохранения.
    """
    ip = _get_client_ip(request)
    save_feedback(
        ip=ip,
        case_id=body.case_id,
        session_id=body.session_id,
        vote=body.vote,
    )
    return {"success": True}


@app.get("/api/metrics")
async def metrics():
    """
    Возвращает агрегированные метрики использования для бэк-офиса.

    Returns:
        dict: Метрики: статистика по IP, кейсам, оценкам, временной ряд.
    """
    return get_metrics()
