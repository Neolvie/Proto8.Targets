# Результаты тестирования

**Агент:** QA Engineer
**Дата:** 2026-02-14 09:40
**Статус:** PASSED

---

## Резюме

Прототип полностью работоспособен: все 96 unit/integration тестов и 16 Playwright E2E тестов проходят. Покрытие кода — 86%. Docker-сборка и запуск контейнера выполнены успешно из чистого состояния. Бэк-офис доступен и отображает корректные метрики.

---

## Docker Verification (МОЙ ЗАПУСК)

### docker-compose down --remove-orphans

```
time="2026-02-14T09:32:27+04:00" level=warning msg="...version is obsolete..."
 Container proto8targets-app-1  Stopping
 Container proto8targets-app-1  Stopped
 Container proto8targets-app-1  Removing
 Container proto8targets-app-1  Removed
 Network proto8targets_default  Removing
 Network proto8targets_default  Removed
```

### docker-compose build --no-cache

```
time="2026-02-14T09:36:10+04:00" ...
#9 [ 4/13] RUN pip install --no-cache-dir -r requirements.txt
#9 43.14 Successfully installed aiofiles-24.1.0 fastapi-0.115.6 openai-1.58.1
  playwright-1.49.1 pydantic-2.10.3 python-docx-1.1.2 uvicorn-0.32.1 [и другие]
#11 Chromium Headless Shell 131.0.6778.33 downloaded to /root/.cache/ms-playwright/
#19 naming to docker.io/library/proto8targets-app:latest done
 proto8targets-app  Built
```

### docker-compose up -d

```
time="2026-02-14T09:36:32+04:00" ...
 Network proto8targets_default  Created
 Container proto8targets-app-1  Created
 Container proto8targets-app-1  Started
```

### Проверка доступности

```
$ curl http://localhost:8000/api/health
{"status":"ok","service":"Directum Targets AI Assistant"}

$ curl http://localhost:8000/ | head -3
<!DOCTYPE html>
<html lang="ru">
<head>

$ curl http://localhost:8000/backoffice | head -3
<!DOCTYPE html>
<html lang="ru">
<head>

$ curl http://localhost:8000/api/metrics
{"total_requests":0,"unique_ips":0,"ip_stats":[],"case_stats":[{"case_id":1,...},...],"timeline":[],"total_positive_pct":null}
```

---

## Выполнение тестов (МОЙ ЗАПУСК)

### pytest --cov=src tests/unit/ tests/integration/ -v

```
platform win32 -- Python 3.12.4, pytest-8.3.4
collected 96 items

tests/unit/test_cases_service.py::TestRunCase::test_invalid_case_id_raises PASSED
tests/unit/test_cases_service.py::TestRunCase::test_cases_1_to_4_6_require_goal[1] PASSED
tests/unit/test_cases_service.py::TestRunCase::test_cases_1_to_4_6_require_goal[2] PASSED
tests/unit/test_cases_service.py::TestRunCase::test_cases_1_to_4_6_require_goal[3] PASSED
tests/unit/test_cases_service.py::TestRunCase::test_cases_1_to_4_6_require_goal[4] PASSED
tests/unit/test_cases_service.py::TestRunCase::test_cases_1_to_4_6_require_goal[6] PASSED
tests/unit/test_cases_service.py::TestRunCase::test_case_with_unknown_goal_id_raises[1] PASSED
... [все 96 тестов PASSED] ...
tests/integration/test_api_metrics.py::TestStaticPages::test_backoffice_contains_metrics_title PASSED

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

96 passed in 1.72s
```

**Coverage: 86% — PASS ✅ (порог ≥70%)**

### pytest tests/e2e/ -v

```
platform win32 -- Python 3.12.4, pytest-8.3.4, playwright-0.6.2
collected 16 items

tests/e2e/test_backoffice.py::test_backoffice_page_loads[chromium] PASSED
tests/e2e/test_backoffice.py::test_backoffice_has_stats_cards[chromium] PASSED
tests/e2e/test_backoffice.py::test_backoffice_has_ip_table[chromium] PASSED
tests/e2e/test_backoffice.py::test_backoffice_has_cases_table[chromium] PASSED
tests/e2e/test_backoffice.py::test_backoffice_refresh_button_works[chromium] PASSED
tests/e2e/test_backoffice.py::test_backoffice_link_to_app[chromium] PASSED
tests/e2e/test_backoffice.py::test_backoffice_shows_case_stats_for_all_7[chromium] PASSED
tests/e2e/test_main_flow.py::test_home_page_loads[chromium] PASSED
tests/e2e/test_main_flow.py::test_upload_section_visible[chromium] PASSED
tests/e2e/test_main_flow.py::test_test_data_button_loads_map[chromium] PASSED
tests/e2e/test_main_flow.py::test_goal_selector_populated[chromium] PASSED
tests/e2e/test_main_flow.py::test_seven_case_cards_visible[chromium] PASSED
tests/e2e/test_main_flow.py::test_upload_json_text[chromium] PASSED
tests/e2e/test_main_flow.py::test_reset_returns_to_upload[chromium] PASSED
tests/e2e/test_main_flow.py::test_tabs_switching[chromium] PASSED
tests/e2e/test_main_flow.py::test_case5_runs_and_shows_result[chromium] PASSED

16 passed in 19.01s
```

---

## Покрытие критериев приёмки

| Критерий | Статус | Комментарий |
|---------|--------|-------------|
| Загрузка JSON-файла | PASS | Drag-and-drop и выбор файла работают |
| Загрузка DOCX-файла | PASS | Файл принимается, текст извлекается |
| Вставка JSON-текста | PASS | Textarea работает |
| Кнопка тестовых данных Ario 2026 | PASS | E2E тест подтверждён |
| Валидация JSON | PASS | 422 при невалидном JSON |
| 7 кейсов OKR | PASS | Все 7 карточек отображаются, кейс 5 запускается |
| SSE streaming | PASS | Ответы передаются потоково |
| Свободный чат | PASS | Вкладка переключается, API работает |
| Кнопки 👍/👎 | PASS | POST /api/feedback возвращает {success: true} |
| Backoffice /backoffice | PASS | Страница загружается, метрики отображаются |
| Метрики по IP | PASS | /api/metrics возвращает ip_stats |
| Частота по времени | PASS | timeline в ответе metrics |
| Графики (Chart.js) | PASS | script из CDN, canvas элементы присутствуют |
| 7 кейсов в бэк-офисе | PASS | E2E тест подтверждён |
| Docker сборка | PASS | Образ собран успешно |
| pytest ≥70% | PASS | 86% покрытия |
| Playwright E2E | PASS | 16/16 тестов прошли |

---

## Ручная проверка UX

- **Главная страница:** Отображает секцию загрузки с кнопкой тестовых данных, drag-and-drop зонами и textarea — понятный интерфейс
- **Загрузка тестовых данных:** Кнопка «Карта целей Ario 2026» загружает данные и переходит к кейсам — работает корректно
- **Список целей:** Dropdown заполняется целями из карты — все 15 целей Ario присутствуют
- **7 карточек кейсов:** Отображаются в сетке с описанием и кнопкой запуска — читаемо и понятно
- **Кейс 5 (не требует цель):** Запускается немедленно, появляется область результата — UX понятен
- **Бэк-офис:** http://localhost:8000/backoffice — загружается, показывает 3 stat-card (запросов, IP, % оценок), таблицы IP и 7 кейсов
- **Обработка ошибок:** Попытка запустить кейс 1 без выбранной цели → сообщение «Кейс 1 требует выбора конкретной цели»
- **UX оценка:** Понятно. Интерфейс минималистичен, каждый элемент выполняет функцию.

---

## Проблемы

### Критичные (блокируют)
- Нет

### Некритичные
- `config.py` покрытие 60% — функции `get_data_dir()` и `get_port()` не покрыты тестами, но не влияют на работу прототипа
- `llm_service.py` покрытие 19% — реальные вызовы OpenAI не тестируются (правильное поведение: mock в тестах), не блокирует

---

## Решение

**PASSED** — передаю в Quality Gate.

Все критерии приёмки выполнены. 112 тестов (96 unit/integration + 16 E2E) PASSED. Покрытие 86%. Docker работает. Бэк-офис доступен и отображает корректные данные.
