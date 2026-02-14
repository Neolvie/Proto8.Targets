# Multi-Agent Prototype Development System

Система для быстрого создания прототипов на основе гипотез.

## Быстрый старт

1. Заполни `.hypothesis/00_HYPOTHESIS.md`
2. Запусти `/pm` — Project Manager запустит весь pipeline

**Режимы работы:**
- `/pm` — запускает PM, который спрашивает что делать дальше (MANUAL по умолчанию)
- `/pm MODE: AUTO` — PM ведёт весь процесс автоматически

**Отдельные агенты (ручной запуск):**
- `/ba` — Business Analyst (анализ гипотезы → `01_REQUIREMENTS.md`)
- `/architect` — Architect (проектирование → `02_ARCHITECTURE.md`)
- `/dev` — Developer (реализация → `04_IMPLEMENTATION.md`)
- `/qa` — QA (тестирование → `05_TEST_RESULTS.md`)
- `/gate` — Quality Gate (финальная проверка → `06_QUALITY_GATE_REPORT.md`)

> **Как работает цепочка:** `/pm` запускает агента `pm` (`.claude/agents/pm.md`), который через инструмент `Task` сам последовательно вызывает агентов `ba → architect → developer → qa → gate`, не останавливаясь между шагами.

## Технологический стек (ОБЯЗАТЕЛЬНО)

- **Python 3.10+**
- **UI:** Vanilla JS (чистый HTML/CSS/JS, без фреймворков)
- **Backend:** FastAPI (обязателен — раздаёт UI и API)
- **Тесты:** pytest ≥70% coverage + Playwright E2E
- **Деплой:** Docker + docker-compose
- **LLM:** только OpenAI Python SDK (не прямые HTTP запросы)
- **Запрещено:** React/Vue/Angular/Next.js/Svelte и любые JS-фреймворки
- **Стили, иконки, логотипы** Directum и Directum Ario: https://www.directum.ru/ui-kit

## Pipeline и файлы

```
00_HYPOTHESIS.md → [BA] → 01_REQUIREMENTS.md → [Architect] → 02_ARCHITECTURE.md
→ [Developer] → 04_IMPLEMENTATION.md → [QA] → 05_TEST_RESULTS.md
→ [Quality Gate] → 06_QUALITY_GATE_REPORT.md
```

Файл `BUILD_LOG.md` ведёт PM на протяжении всего процесса.

## Критичные правила

- **Реальное выполнение**: агенты ОБЯЗАНЫ запускать команды, не имитировать
- **Docker-first**: всё верифицируется в Docker
- **Backoffice обязателен**: каждый прототип содержит страницу метрик (IP, рейтинги, частота)
- **`.env` не трогать**: никогда не создавать, не редактировать, не перезаписывать `.env`
- **Один источник правды**: только файлы из `.hypothesis/`, `src/`, `tests/`

## Правила общения

- Агентные инструкции: English
- Общение с пользователем: Russian
- Docstrings: Russian

## Переменные окружения

`.env` в корне проекта (не трогать!):
- `OPENAI_API_KEY` — обязательно
- `OPENAI_MODEL` — обязательно
- `OPENAI_SERVER` — опционально (кастомный endpoint)

## Механизм эскалации

Если агент застрял (>5 попыток) → пишет в `BUILD_LOG.md` блок `[BLOCKER]` и уведомляет пользователя.

Если QA нашёл проблему в архитектуре (не в коде) → эскалация через PM обратно к Architect.

## Детальные правила

Полные правила системы: `.cursor/rules.md`
Инструкции агентов для Cursor: `.cursor/*-agent.md`
Агенты Claude Code (subagents): `.claude/agents/*.md`
