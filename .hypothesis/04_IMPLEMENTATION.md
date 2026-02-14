# Реализация прототипа

**Агент:** Developer
**Дата:** 2026-02-14 09:15
**Статус:** Готово

---

## Резюме

Реализован ИИ-помощник для работы с целями Directum Targets: FastAPI + Vanilla JS + SQLite + OpenAI SDK. Поддерживает загрузку JSON-карты целей, DOCX-описания, 7 OKR-кейсов со streaming, свободный чат, оценки 👍/👎 и бэк-офис метрик.

---

## Структура проекта

```
src/
  __init__.py
  main.py                      — FastAPI app, 9 маршрутов, middleware IP
  config.py                    — Конфигурация из .env через load_dotenv
  models/
    __init__.py
    targets.py                 — Pydantic модели GoalNode, GoalsMap
    api.py                     — Pydantic модели запросов/ответов API
  services/
    __init__.py
    llm_service.py             — OpenAI SDK streaming
    cases_service.py           — 7 кейсов OKR-анализа с промптами
    chat_service.py            — Свободный чат с историей
    json_parser.py             — Парсер карты целей Directum Targets
    docx_parser.py             — Парсер DOCX через python-docx
    metrics_storage.py         — SQLite метрики (requests, feedback)
  static/
    index.html                 — Главная страница (загрузка, кейсы, чат)
    style.css                  — Стили (Directum UI Kit цвета)
    app.js                     — Логика фронтенда (fetch, SSE, DOM)
    backoffice.html            — Страница метрик /backoffice
    backoffice.js              — Логика бэк-офиса (Chart.js графики)
data/
  Ario.json                   — Тестовая карта целей БЕ Ario
  Ario.docx                   — Тестовый DOCX с описанием целей
tests/
  conftest.py                  — Общие фикстуры (TestClient, temp DB)
  unit/
    test_json_parser.py        — Тесты парсера JSON (15 тестов)
    test_docx_parser.py        — Тесты парсера DOCX (9 тестов)
    test_cases_service.py      — Тесты кейсов OKR (16 тестов)
    test_chat_service.py       — Тесты чат сервиса (5 тестов)
    test_metrics_storage.py    — Тесты SQLite метрик (12 тестов)
  integration/
    test_api_data.py           — API тесты загрузки данных (7 тестов)
    test_api_feedback.py       — API тесты обратной связи (7 тестов)
    test_api_metrics.py        — API тесты метрик и страниц (8 тестов)
    test_api_cases.py          — API тесты кейсов (7 тестов)
  e2e/
    test_main_flow.py          — Playwright E2E основной сценарий
    test_backoffice.py         — Playwright E2E бэк-офис
requirements.txt
Dockerfile
docker-compose.yml
pytest.ini
.coveragerc
.env.example
TECHNICAL_DOCUMENTATION.md
```

---

## Реализованные требования

- [x] FR-01: Загрузка JSON-файла карты целей (drag-and-drop, выбор файла)
- [x] FR-02: Загрузка DOCX-файла описания цели
- [x] FR-03: Вставка JSON-текста в textarea
- [x] FR-04: Кнопка «Тестовая карта целей: Ario 2026» — подгружает Ario.json + Ario.docx
- [x] FR-05: Валидация структуры JSON с понятными ошибками
- [x] FR-06: Кейс 1 — SMART-анализ формулировки цели
- [x] FR-07: Кейс 2 — Генерация 3-4 наборов KR
- [x] FR-08: Кейс 3 — Квартальная декомпозиция годовой цели
- [x] FR-09: Кейс 4 — Верификация по ожиданиям руководства
- [x] FR-10: Кейс 5 — Конфликты и слепые зоны всей карты
- [x] FR-11: Кейс 6 — Матрица рисков достижения цели
- [x] FR-12: Кейс 7 — Экспресс-отчёт для руководства
- [x] FR-13: Свободный чат с ИИ-помощником
- [x] FR-14: История чата в sessionStorage
- [x] FR-15: Кнопки 👍/👎 с сохранением оценок в SQLite
- [x] FR-16: Обновление оценки при повторном голосовании (INSERT OR REPLACE)
- [x] FR-17: Обработка превышения контекста LLM
- [x] FR-18: SSE streaming для LLM ответов
- [x] FR-19: Страница /backoffice с метриками
- [x] Backoffice: метрики по IP, оценки по кейсам, частота по дням, Chart.js графики

---

## Docker Verification (СОБСТВЕННЫЙ ВЫВОД)

### docker-compose build

```
time="2026-02-14T09:06:10+04:00" level=warning msg="...version is obsolete..."
#9 [ 4/13] RUN pip install --no-cache-dir -r requirements.txt
#9 43.14 Successfully installed aiofiles-24.1.0 annotated-types-0.7.0 anyio-4.12.1
  certifi-2026.1.4 charset_normalizer-3.4.4 click-8.3.1 coverage-7.13.4
  fastapi-0.115.6 httpx-0.28.1 openai-1.58.1 playwright-1.49.1
  pydantic-2.10.3 pytest-8.3.4 python-docx-1.1.2 python-dotenv-1.0.1
  uvicorn-0.32.1 [и другие пакеты]
#11 Chromium Headless Shell 131.0.6778.33 (playwright build v1148) downloaded to /root/.cache/ms-playwright/
#19 exporting manifest sha256:a22758922dcd5e76a930d40abb7e10828d699baa2b765c58252c478b678e6584 done
#19 naming to docker.io/library/proto8targets-app:latest done
 proto8targets-app  Built
```

### docker-compose up -d

```
time="2026-02-14T09:12:55+04:00" level=warning msg="...version is obsolete..."
 Network proto8targets_default  Creating
 Network proto8targets_default  Created
 Container proto8targets-app-1  Creating
 Container proto8targets-app-1  Created
 Container proto8targets-app-1  Starting
 Container proto8targets-app-1  Started
```

### curl http://localhost:8000/api/health

```json
{"status":"ok","service":"Directum Targets AI Assistant"}
```

### curl http://localhost:8000/

```html
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <title>ИИ-помощник Directum Targets</title>
  ...
```

### curl http://localhost:8000/backoffice

```html
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <title>Бэк-офис — Directum Targets AI</title>
  ...
```

### curl http://localhost:8000/api/metrics

```json
{
  "total_requests": 0, "unique_ips": 0, "ip_stats": [],
  "case_stats": [
    {"case_id": 1, "requests": 0, "positive": 0, "negative": 0, "pct_positive": null},
    {"case_id": 2, "requests": 0, ...},
    ...7 кейсов...
  ],
  "timeline": [], "total_positive_pct": null
}
```

### pytest --cov=src tests/ -v

```
============================= test session starts =============================
platform win32 -- Python 3.12.4
rootdir: C:\Projects\Claude\Proto8.Targets
plugins: asyncio-0.24.0, cov-6.0.0, playwright-0.6.2

collected 96 items

tests/unit/test_cases_service.py::TestRunCase::test_invalid_case_id_raises PASSED
tests/unit/test_cases_service.py::TestRunCase::test_cases_1_to_4_6_require_goal[1] PASSED
... [все 96 тестов] ...

---------- coverage: platform win32, python 3.12.4-final-0 -----------
Name                              Stmts   Miss  Cover   Missing
---------------------------------------------------------------
src/__init__.py                       0      0   100%
src/config.py                        15      6    60%
src/main.py                         137     36    74%
src/models/__init__.py                0      0   100%
src/models/api.py                    33      0   100%
src/models/targets.py                25      0   100%
src/services/__init__.py              0      0   100%
src/services/cases_service.py        64      1    98%
src/services/chat_service.py         17      0   100%
src/services/docx_parser.py          60      3    95%
src/services/json_parser.py          67      4    94%
src/services/llm_service.py          26     21    19%
src/services/metrics_storage.py      64      0   100%
---------------------------------------------------------------
TOTAL                               508     71    86%

96 passed in 1.69s
```

**Coverage: 86% ✅ (порог: ≥70%)**

---

## Конфигурация

- `.env` в корне проекта (не создаётся, не редактируется агентом). Переменные из .env передаются в контейнер через docker-compose env_file. Dockerfile содержит `COPY .env.example .env.example`.
- Порт приложения: **8000**
- Приложение URL: http://localhost:8000
- Backoffice URL: http://localhost:8000/backoffice
- Переменные: `OPENAI_API_KEY`, `OPENAI_MODEL`, опционально `OPENAI_SERVER`
- Data dir: `/app/data` (монтируется как том Docker для персистентности metrics.db)

---

## Технические решения

| Решение | Обоснование |
|---------|------------|
| SSE вместо WebSocket | Однонаправленный стриминг; проще реализация FastAPI + Vanilla JS |
| SQLite встроенная | Без внешних зависимостей; достаточно для прототипа |
| sessionStorage для чата | Не требует серверного хранения; простота реализации |
| `_case*` функции как sync | Функции сразу бросают ValueError для проверки goal; возвращают coroutine LLM |
| `INSERT OR REPLACE` для feedback | Предотвращает дубли оценок от одной сессии |
| Chart.js через CDN | Нет build-шага; достаточно для прототипа |

---

## Следующие шаги

Передать QA для независимого тестирования.
