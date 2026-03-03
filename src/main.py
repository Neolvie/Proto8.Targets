"""Главный модуль FastAPI приложения ИИ-помощника для Directum Targets."""

import os
import json
import secrets
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_data_dir, get_targets_base_url, get_backoffice_credentials
from src.models.api import (
    CaseRequest, ChatRequest, FeedbackRequest, ChatFeedbackRequest,
    DataLoadResponse, GoalListItem, JsonUploadRequest,
)
from src.services.json_parser import parse_goals_map, format_map_for_llm
from src.services.docx_parser import parse_docx_bytes, parse_docx_file
from src.services import cases_service, chat_service, targets_api, context_builder
from src.services.metrics_storage import (
    init_db, log_request, save_feedback,
    save_chat_feedback, update_chat_feedback_summary, get_metrics,
)
from src.services.llm_service import get_completion

_basic_security = HTTPBasic(auto_error=True)

# Инициализация базы данных при запуске
init_db()

app = FastAPI(
    title="Directum Targets AI Assistant",
    description="ИИ-помощник для работы с целями и KR из Directum Targets",
    version="2.0.0",
)

# Session-based кэширование (in-memory)
app.state.cache = {}

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


def _check_backoffice_auth(credentials: HTTPBasicCredentials = Depends(_basic_security)):
    """
    Проверяет Basic Auth для доступа к бэкофису.

    Raises:
        HTTPException 401: Если логин или пароль неверны.
    """
    username, password = get_backoffice_credentials()
    ok = (
        secrets.compare_digest(credentials.username.encode(), username.encode())
        and secrets.compare_digest(credentials.password.encode(), password.encode())
    )
    if not ok:
        raise HTTPException(
            status_code=401,
            detail="Неверные логин или пароль",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


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
async def backoffice(request: Request, _: str = Depends(_check_backoffice_auth)):
    """Страница метрик бэк-офиса (защищена Basic Auth)."""
    backoffice_path = static_dir / "backoffice.html"
    if not backoffice_path.exists():
        raise HTTPException(status_code=404, detail="backoffice.html не найден")
    return HTMLResponse(content=backoffice_path.read_text(encoding="utf-8"))


@app.get("/api/health")
async def health():
    """Healthcheck endpoint."""
    return {"status": "ok", "service": "Directum Targets AI Assistant"}


# ===== V2 API ENDPOINTS (Targets API Integration) =====

@app.get("/api/maps")
async def get_maps_endpoint(request: Request, period: Optional[str] = None):
    """
    Возвращает список карт целей с фильтрацией по периоду.

    Args:
        period: Значение PeriodLabel для фильтрации (опционально).

    Returns:
        dict: {"maps": [...], "periods": [...]}.
    """
    # Проверка наличия настроек Targets API
    if not get_targets_base_url():
        return {
            "maps": [],
            "periods": [],
            "error": "Targets API не настроен. Установите TARGETS_BASE_URL и TARGETS_TOKEN в .env"
        }

    session_id = request.headers.get("X-Session-Id", "default")
    ip = _get_client_ip(request)
    log_request(ip, "/api/maps")

    # Проверка кэша
    if session_id not in app.state.cache:
        app.state.cache[session_id] = {"maps": None, "map_graph": {}, "targets": {}}

    cache = app.state.cache[session_id]

    # Загрузка карт если не в кэше
    if cache["maps"] is None:
        maps = await targets_api.get_maps()
        cache["maps"] = maps
    else:
        maps = cache["maps"]

    # Извлечение уникальных периодов
    periods = sorted(list(set(m.PeriodLabel for m in maps)))

    # Фильтрация по периоду
    if period:
        filtered_maps = [m for m in maps if m.PeriodLabel == period]
    else:
        filtered_maps = maps

    # Формирование ответа
    maps_data = [
        {
            "id": m.Id,
            "name": m.Name,
            "code": m.Code,
            "period_label": m.PeriodLabel,
            "achievement_percentage": m.AchievementPercentage,
            "status": m.Status,
        }
        for m in filtered_maps
    ]

    return {"maps": maps_data, "periods": periods}


@app.get("/api/maps/{map_id}/goals")
async def get_map_goals(map_id: int, request: Request):
    """
    Возвращает граф целей карты (список узлов).

    Args:
        map_id: ID карты.

    Returns:
        dict: {"map": {...}, "nodes": [...]}.
    """
    session_id = request.headers.get("X-Session-Id", "default")
    ip = _get_client_ip(request)
    log_request(ip, f"/api/maps/{map_id}/goals")

    if session_id not in app.state.cache:
        app.state.cache[session_id] = {"maps": None, "map_graph": {}, "targets": {}}

    cache = app.state.cache[session_id]

    # Загрузка графа если не в кэше
    if map_id not in cache["map_graph"]:
        graph = await targets_api.get_map_graph(map_id)
        cache["map_graph"][map_id] = graph
    else:
        graph = cache["map_graph"][map_id]

    # Формирование ответа
    map_info = {
        "id": graph.Map.Id if graph.Map else 0,
        "name": graph.Map.Name if graph.Map else "",
        "progress": graph.Map.Progress if graph.Map else 0.0,
    }

    nodes_data = [
        {
            "target_id": node.TargetId,
            "code": node.Code,
            "name": node.Name,
            "progress": node.Progress,
            "status_name": (node.Status.Name or "—") if node.Status else "—",
            "status_icon": node.Status.Icon if node.Status else None,
            "priority": node.Priority,
            "responsible_name": (node.Responsible.Name or "—") if node.Responsible else "—",
            "period_name": (node.Period.Name or "—") if node.Period else "—",
            "key_result_count": node.KeyResultCount,
        }
        for node in graph.Nodes
    ]

    return {"map": map_info, "nodes": nodes_data}


@app.get("/api/targets/{target_id}")
async def get_target_endpoint(target_id: int, request: Request):
    """
    Возвращает расширенную информацию по цели + ключевые результаты.

    Args:
        target_id: ID цели.

    Returns:
        dict: {"target": {...}, "key_results": [...]}.
    """
    session_id = request.headers.get("X-Session-Id", "default")
    ip = _get_client_ip(request)
    log_request(ip, f"/api/targets/{target_id}")

    if session_id not in app.state.cache:
        app.state.cache[session_id] = {"maps": None, "map_graph": {}, "targets": {}}

    cache = app.state.cache[session_id]

    # Загрузка цели и КР если не в кэше
    if target_id not in cache["targets"]:
        target = await targets_api.get_target(target_id)
        key_results = await targets_api.get_key_results(target_id)
        cache["targets"][target_id] = {"detail": target, "key_results": key_results}
    else:
        target = cache["targets"][target_id]["detail"]
        key_results = cache["targets"][target_id]["key_results"]

    # Формирование ответа
    target_data = {
        "id": target.Id,
        "name": target.Name,
        "code": target.Code,
        "status_description": target.StatusDescription,
        "period_label": target.PeriodLabel,
        "achievement_percentage": target.AchievementPercentage,
        "period_start": target.PeriodStart,
        "period_end": target.PeriodEnd,
        "is_personal": target.IsPersonal,
        "description": target.Description,
        "notes": target.Notes,
        "priority": target.Priority,
    }

    kr_data = [
        {
            "description": kr.Description,
            "achievement_percentage": kr.AchievementPercentage,
            "metric": kr.Metric,
            "initial_value": kr.InitialValue,
            "planned_value": kr.PlannedValue,
            "actual_value": kr.ActualValue,
        }
        for kr in key_results
    ]

    return {"target": target_data, "key_results": kr_data}


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




@app.post("/api/cases/{case_id}")
async def run_case(case_id: int, request: Request):
    """
    Запускает один из 7 кейсов OKR-анализа с потоковым ответом (SSE).

    Поддерживает v1 (с goals_map) и v2 (с map_id/target_id) форматы запросов.

    Args:
        case_id: Номер кейса (1-7).

    Returns:
        StreamingResponse: Поток текстовых фрагментов в формате SSE.

    Raises:
        HTTPException: Если кейс не найден или контекст не задан.
    """
    if case_id not in (1, 2, 3, 5, 6, 7):
        raise HTTPException(status_code=400, detail="Допустимые кейсы: 1, 2, 3, 5, 6, 7")

    ip = _get_client_ip(request)
    log_request(ip, f"/api/cases/{case_id}", case_id=case_id)

    # Получаем тело запроса как JSON
    body_json = await request.json()

    # Определяем, v1 или v2 формат
    # v2 формат: mode, map_id, target_id, session_id
    # v1 формат: goals_map, selected_goal_id, docx_content
    is_v2 = "mode" in body_json or "map_id" in body_json or "target_id" in body_json

    try:
        if is_v2:
            # V2 API: используем кэш и строковые контексты
            session_id = request.headers.get("X-Session-Id", "default")
            mode = body_json.get("mode")
            map_id = body_json.get("map_id")
            target_id = body_json.get("target_id")

            if session_id not in app.state.cache:
                raise HTTPException(status_code=400, detail="Сессия не найдена. Загрузите карту целей.")

            cache = app.state.cache[session_id]

            # Строим контексты
            map_context = None
            target_context = None

            if mode == "map" and map_id is not None:
                # Режим карты — используем граф карты
                if map_id not in cache["map_graph"]:
                    raise HTTPException(status_code=400, detail=f"Карта {map_id} не загружена в сессии.")
                graph = cache["map_graph"][map_id]
                # Формируем текстовый контекст карты
                map_context = context_builder.build_map_context(
                    nodes=graph.Nodes,
                    map_info=cache["maps"][0] if cache["maps"] else None  # Находим карту по ID
                )
                # Ищем карту в списке
                for m in cache["maps"]:
                    if m.Id == map_id:
                        map_context = context_builder.build_map_context(graph.Nodes, m)
                        break

            elif mode == "target" and target_id is not None:
                # Режим цели — используем детали цели
                if target_id not in cache["targets"]:
                    raise HTTPException(status_code=400, detail=f"Цель {target_id} не загружена в сессии.")
                target_data = cache["targets"][target_id]
                target_context = context_builder.build_target_context(
                    target=target_data["detail"],
                    key_results=target_data["key_results"]
                )

            generator = await cases_service.run_case_v2(
                case_id=case_id,
                map_context=map_context,
                target_context=target_context,
            )
        else:
            # V1 API: используем GoalsMap напрямую
            from src.models.api import CaseRequest
            body = CaseRequest(**body_json)
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
                yield f"data: {json.dumps(chunk)}\n\n"
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
async def chat(request: Request):
    """
    Выполняет запрос к свободному чату с ИИ-помощником с потоковым ответом (SSE).

    Поддерживает v1 (с goals_map) и v2 (с map_id/target_id) форматы запросов.

    Returns:
        StreamingResponse: Поток текстовых фрагментов в формате SSE.
    """
    ip = _get_client_ip(request)
    log_request(ip, "/api/chat")

    # Получаем тело запроса как JSON
    body_json = await request.json()

    # Определяем, v1 или v2 формат
    is_v2 = "mode" in body_json or "map_id" in body_json or "target_id" in body_json

    try:
        if is_v2:
            # V2 API
            from src.models.api import ChatMessage
            session_id = request.headers.get("X-Session-Id", "default")
            mode = body_json.get("mode")
            map_id = body_json.get("map_id")
            target_id = body_json.get("target_id")
            messages = [ChatMessage(**m) for m in body_json.get("messages", [])]

            if session_id not in app.state.cache:
                raise HTTPException(status_code=400, detail="Сессия не найдена. Загрузите карту целей.")

            cache = app.state.cache[session_id]

            # Строим контексты
            map_context = None
            target_context = None

            if mode == "map" and map_id is not None:
                if map_id not in cache["map_graph"]:
                    raise HTTPException(status_code=400, detail=f"Карта {map_id} не загружена в сессии.")
                graph = cache["map_graph"][map_id]
                # Ищем карту в списке
                for m in cache["maps"]:
                    if m.Id == map_id:
                        map_context = context_builder.build_map_context(graph.Nodes, m)
                        break

            elif mode == "target" and target_id is not None:
                if target_id not in cache["targets"]:
                    raise HTTPException(status_code=400, detail=f"Цель {target_id} не загружена в сессии.")
                target_data = cache["targets"][target_id]
                target_context = context_builder.build_target_context(
                    target=target_data["detail"],
                    key_results=target_data["key_results"]
                )

            generator = await chat_service.run_chat_v2(
                map_context=map_context,
                target_context=target_context,
                messages=messages,
            )
        else:
            # V1 API
            from src.models.api import ChatRequest
            body = ChatRequest(**body_json)
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
                yield f"data: {json.dumps(chunk)}\n\n"
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


@app.post("/api/feedback/chat/summarize")
async def summarize_chat_feedback(request: Request):
    """
    Асинхронно генерирует краткое резюме (2-3 слова) запроса пользователя через LLM
    и сохраняет его в запись chat_feedback.

    Body: {"id": int, "user_message": str}

    Returns:
        dict: {"summary": str} — сгенерированное резюме.
    """
    body_json = await request.json()
    feedback_id = body_json.get("id")
    user_message = body_json.get("user_message", "")

    if not feedback_id or not user_message:
        raise HTTPException(status_code=400, detail="Необходимы поля id и user_message")

    try:
        summary = await get_completion([
            {
                "role": "system",
                "content": (
                    "Сократи вопрос пользователя до 2-3 слов (тема запроса). "
                    "Отвечай только этими словами, без знаков препинания и пояснений."
                ),
            },
            {"role": "user", "content": user_message},
        ])
        # Обрезаем до разумного максимума на случай неожиданного ответа модели
        summary = summary[:60]
        update_chat_feedback_summary(feedback_id, summary)
        return {"summary": summary}
    except Exception as e:
        # При любой ошибке не ломаем клиент — просто не обновляем summary
        logger.error("summarize_chat_feedback failed for id=%s: %s", feedback_id, e)
        return {"summary": None}


@app.get("/api/metrics")
async def metrics(_: str = Depends(_check_backoffice_auth)):
    """
    Возвращает агрегированные метрики использования для бэк-офиса.

    Returns:
        dict: Метрики: статистика по IP, кейсам, оценкам, временной ряд.
    """
    return get_metrics()


@app.post("/api/feedback/chat")
async def chat_feedback(request: Request, body: ChatFeedbackRequest):
    """
    Сохраняет оценку (👍/👎) ответа свободного чата с контекстом запроса.

    Args:
        body: vote, session_id, user_message, context_type, context_name.

    Returns:
        dict: Подтверждение сохранения.
    """
    ip = _get_client_ip(request)
    feedback_id = save_chat_feedback(
        ip=ip,
        session_id=body.session_id,
        vote=body.vote,
        user_message=body.user_message,
        context_type=body.context_type,
        context_name=body.context_name,
    )
    return {"success": True, "id": feedback_id}
