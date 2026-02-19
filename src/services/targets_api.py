"""Асинхронный HTTP-клиент для Directum Targets API."""

import logging
from typing import List
import httpx
from fastapi import HTTPException
from pydantic import ValidationError

from src.config import get_targets_base_url, get_targets_token
from src.models.targets import TargetsMap, MapGraph, TargetDetail, KeyResult

logger = logging.getLogger("targets_api")


async def get_maps() -> List[TargetsMap]:
    """
    Загружает список карт целей из Targets API.

    GET {TARGETS_BASE_URL}/Integration/odata/ITargetsTargetsMaps
    Authorization: Bearer {TARGETS_TOKEN}

    Returns:
        List[TargetsMap]: Список карт с полями Id, Name, Code, PeriodLabel,
                          AchievementPercentage, Status.

    Raises:
        HTTPException: При ошибках авторизации, доступа или таймауте.
    """
    base_url = get_targets_base_url()
    token = get_targets_token()

    if not base_url or not token:
        raise HTTPException(
            status_code=500,
            detail="TARGETS_BASE_URL и TARGETS_TOKEN должны быть заданы в .env"
        )

    url = f"{base_url}/Integration/odata/ITargetsTargetsMaps"
    # Токен передаётся как есть — он может уже содержать схему (Bearer/Basic)
    token_clean = token.strip('"').strip("'")
    headers = {"Authorization": token_clean}
    logger.warning("GET %s | Authorization: %s", url,
                   token_clean[:50] + "..." if len(token_clean) > 50 else token_clean)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            logger.warning("Response %s | status=%s | body[:300]=%s",
                           url, response.status_code, response.text[:300])

            if response.status_code == 401:
                raise HTTPException(
                    status_code=401,
                    detail=f"Ошибка авторизации (401). Ответ сервера: {response.text[:300]}"
                )
            elif response.status_code == 403:
                raise HTTPException(
                    status_code=403,
                    detail=f"Доступ запрещён (403). Ответ сервера: {response.text[:300]}"
                )
            elif response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"Endpoint не найден (404). Ответ сервера: {response.text[:300]}"
                )
            elif response.status_code >= 500:
                raise HTTPException(
                    status_code=500,
                    detail=f"Ошибка API Targets ({response.status_code}): {response.text[:300]}"
                )

            response.raise_for_status()
            data = response.json()

            # Ожидаем формат {"value": [...]}
            if isinstance(data, dict) and "value" in data:
                maps_data = data["value"]
            else:
                maps_data = data if isinstance(data, list) else []

            # Валидация и фильтрация через Pydantic
            maps = []
            for item in maps_data:
                try:
                    maps.append(TargetsMap(**item))
                except ValidationError:
                    # Пропускаем невалидные записи
                    continue

            return maps

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Таймаут API Targets. Повторите запрос позже."
        )
    except httpx.HTTPStatusError as e:
        # Обработка других HTTP ошибок
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Ошибка при запросе к Targets API: {e.response.text}"
        )


async def get_map_graph(map_id: int) -> MapGraph:
    """
    Загружает граф целей карты из Targets API.

    POST {TARGETS_BASE_URL}/integration/odata/Targets/GetGoalsMap
    Body: {"mapId": map_id}

    Returns:
        MapGraph: Объект с полями Nodes (список GoalNode) и Map.

    Raises:
        HTTPException: При ошибках авторизации, доступа или таймауте.
    """
    base_url = get_targets_base_url()
    token = get_targets_token()

    if not base_url or not token:
        raise HTTPException(
            status_code=500,
            detail="TARGETS_BASE_URL и TARGETS_TOKEN должны быть заданы в .env"
        )

    url = f"{base_url}/integration/odata/Targets/GetGoalsMap"
    token_clean = token.strip('"').strip("'")
    headers = {
        "Authorization": token_clean,
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json={"mapId": map_id})

            if response.status_code == 401:
                raise HTTPException(
                    status_code=401,
                    detail="Bearer-токен истёк. Обновите TARGETS_TOKEN в .env и перезапустите приложение."
                )
            elif response.status_code == 403:
                raise HTTPException(
                    status_code=403,
                    detail="Доступ запрещён. Проверьте права токена."
                )
            elif response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"Карта с ID {map_id} не найдена."
                )
            elif response.status_code >= 500:
                raise HTTPException(
                    status_code=500,
                    detail=f"Ошибка API Targets: {response.text}"
                )

            response.raise_for_status()
            data = response.json()

            # Валидация через Pydantic
            try:
                return MapGraph(**data)
            except ValidationError as e:
                raise HTTPException(
                    status_code=422,
                    detail=f"Невалидная структура ответа API: {str(e)}"
                )

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Таймаут API Targets. Повторите запрос позже."
        )


async def get_target(target_id: int) -> TargetDetail:
    """
    Загружает расширенную информацию по цели из Targets API.

    GET {TARGETS_BASE_URL}/Integration/odata/ITargetsTargets({target_id})

    Returns:
        TargetDetail: Объект с полями Id, Name, Code, StatusDescription,
                      PeriodLabel, AchievementPercentage, Description, Notes, Priority.

    Raises:
        HTTPException: При ошибках авторизации, доступа или таймауте.
    """
    base_url = get_targets_base_url()
    token = get_targets_token()

    if not base_url or not token:
        raise HTTPException(
            status_code=500,
            detail="TARGETS_BASE_URL и TARGETS_TOKEN должны быть заданы в .env"
        )

    url = f"{base_url}/Integration/odata/ITargetsTargets({target_id})"
    token_clean = token.strip('"').strip("'")
    headers = {"Authorization": token_clean}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)

            if response.status_code == 401:
                raise HTTPException(
                    status_code=401,
                    detail="Bearer-токен истёк. Обновите TARGETS_TOKEN в .env и перезапустите приложение."
                )
            elif response.status_code == 403:
                raise HTTPException(
                    status_code=403,
                    detail="Доступ запрещён. Проверьте права токена."
                )
            elif response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"Цель с ID {target_id} не найдена."
                )
            elif response.status_code >= 500:
                raise HTTPException(
                    status_code=500,
                    detail=f"Ошибка API Targets: {response.text}"
                )

            response.raise_for_status()
            data = response.json()

            # Валидация через Pydantic
            try:
                return TargetDetail(**data)
            except ValidationError as e:
                raise HTTPException(
                    status_code=422,
                    detail=f"Невалидная структура ответа API: {str(e)}"
                )

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Таймаут API Targets. Повторите запрос позже."
        )


async def get_key_results(target_id: int) -> List[KeyResult]:
    """
    Загружает ключевые результаты цели из Targets API.

    GET {TARGETS_BASE_URL}/integration/odata/Targets/GetKeyResults(targetId={target_id})

    Returns:
        List[KeyResult]: Список КР с полями Description, AchievementPercentage,
                         Metric, InitialValue, PlannedValue, ActualValue.

    Raises:
        HTTPException: При ошибках авторизации, доступа или таймауте.
    """
    base_url = get_targets_base_url()
    token = get_targets_token()

    if not base_url or not token:
        raise HTTPException(
            status_code=500,
            detail="TARGETS_BASE_URL и TARGETS_TOKEN должны быть заданы в .env"
        )

    url = f"{base_url}/integration/odata/Targets/GetKeyResults(targetId={target_id})"
    token_clean = token.strip('"').strip("'")
    headers = {"Authorization": token_clean}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)

            if response.status_code == 401:
                raise HTTPException(
                    status_code=401,
                    detail="Bearer-токен истёк. Обновите TARGETS_TOKEN в .env и перезапустите приложение."
                )
            elif response.status_code == 403:
                raise HTTPException(
                    status_code=403,
                    detail="Доступ запрещён. Проверьте права токена."
                )
            elif response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"КР для цели {target_id} не найдены."
                )
            elif response.status_code >= 500:
                raise HTTPException(
                    status_code=500,
                    detail=f"Ошибка API Targets: {response.text}"
                )

            response.raise_for_status()
            data = response.json()

            # Ожидаем формат {"Payload": {"Data": [...]}}
            if isinstance(data, dict) and "Payload" in data and "Data" in data["Payload"]:
                kr_data = data["Payload"]["Data"]
            else:
                kr_data = []

            # Валидация через Pydantic
            key_results = []
            for item in kr_data:
                try:
                    key_results.append(KeyResult(**item))
                except ValidationError:
                    # Пропускаем невалидные записи
                    continue

            return key_results

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Таймаут API Targets. Повторите запрос позже."
        )
