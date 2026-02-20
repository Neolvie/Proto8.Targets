# BUILD LOG — версия 2 (API интеграция)

## Метаданные

- **Начало разработки:** 2026-02-19 14:15
- **Гипотеза:** new_hypothesis/001_HYPOTHESIS.md
- **Режим:** AUTO
- **Ветка:** with_api
- **Project Manager:** Claude Opus 4.6

---

## [2026-02-19 14:15] [PM] — INIT

**Контекст:**
- Прототип v1 работает с загрузкой JSON/DOCX файлов
- v2 заменяет загрузку на прямую API-интеграцию с Directum Targets
- Существующий код должен быть максимально переиспользован: SSE streaming, renderMarkdown(), AbortController, cases_service, metrics_storage

**Ключевые изменения v2:**
1. Удалить загрузку файлов → API интеграция
2. Новые env: TARGETS_BASE_URL, TARGETS_TOKEN
3. Новый UI: период → карты → цели (опционально)
4. 4 API-запроса к Targets
5. Нормализация текста (escape-символы)
6. Компактный текстовый формат для LLM
7. Сессионное кеширование
8. Адаптивные кейсы (map-mode vs target-mode)
9. Кнопка "Новая беседа"

**Следующий шаг:** запуск Business Analyst для анализа новой гипотезы и создания v2_01_REQUIREMENTS.md

---
