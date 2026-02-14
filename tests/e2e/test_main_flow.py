"""Playwright E2E тесты основного пользовательского сценария."""

import pytest
from playwright.sync_api import Page, expect


BASE_URL = "http://localhost:8000"


def test_home_page_loads(page: Page):
    """Главная страница загружается с корректным заголовком."""
    page.goto(BASE_URL)
    title = page.title()
    assert "Targets" in title or "Directum" in title, f"Неожиданный заголовок: {title}"
    # Кнопка тестовых данных присутствует
    expect(page.locator("#btn-load-test")).to_be_visible()


def test_upload_section_visible(page: Page):
    """Секция загрузки файлов отображается на главной странице."""
    page.goto(BASE_URL)
    expect(page.locator("#section-upload")).to_be_visible()
    expect(page.locator("#section-main")).not_to_be_visible()


def test_test_data_button_loads_map(page: Page):
    """Кнопка тестовых данных загружает карту целей и переходит к секции кейсов."""
    page.goto(BASE_URL)

    # Нажимаем кнопку тестовых данных
    page.locator("#btn-load-test").click()

    # Ожидаем перехода к основной секции (с таймаутом)
    expect(page.locator("#section-main")).to_be_visible(timeout=10000)
    expect(page.locator("#section-upload")).not_to_be_visible()


def test_goal_selector_populated(page: Page):
    """После загрузки карты список целей заполняется."""
    page.goto(BASE_URL)
    page.locator("#btn-load-test").click()

    expect(page.locator("#section-main")).to_be_visible(timeout=10000)

    goal_select = page.locator("#goal-select")
    # Должно быть больше одной опции (пустая + цели)
    options = goal_select.locator("option").all()
    assert len(options) > 1


def test_seven_case_cards_visible(page: Page):
    """После загрузки карты отображаются 7 карточек кейсов."""
    page.goto(BASE_URL)
    page.locator("#btn-load-test").click()
    expect(page.locator("#section-main")).to_be_visible(timeout=10000)

    case_cards = page.locator(".case-card").all()
    assert len(case_cards) == 7


def test_upload_json_text(page: Page):
    """Загрузка JSON через текстовое поле работает корректно."""
    page.goto(BASE_URL)

    sample_json = '''{
      "Payload": {
        "Nodes": [
          {
            "Id": "1", "TargetId": 1, "Code": "TEST-1", "Name": "Тестовая цель",
            "ParentId": null, "ChildIds": [], "Priority": "High", "Progress": 50.0,
            "KeyResultCount": 2,
            "Status": {"State": "Active", "Name": "В работе", "Icon": null, "LastAchievementStatus": null},
            "Responsible": {"Name": "Тестов"}, "StructuralUnit": {"Name": "Тест"},
            "Period": {"Name": "2026 год", "TimeFrame": "Year"}
          }
        ],
        "Map": {"Id": 1, "Name": "Тест карта", "Progress": 50.0}
      }
    }'''

    page.locator("#json-text-input").fill(sample_json)
    page.locator("button:has-text('Загрузить и начать')").click()

    expect(page.locator("#section-main")).to_be_visible(timeout=8000)


def test_reset_returns_to_upload(page: Page):
    """Кнопка сброса возвращает на экран загрузки."""
    page.goto(BASE_URL)
    page.locator("#btn-load-test").click()
    expect(page.locator("#section-main")).to_be_visible(timeout=10000)

    page.locator("button:has-text('Загрузить другую')").click()
    expect(page.locator("#section-upload")).to_be_visible(timeout=3000)


def test_tabs_switching(page: Page):
    """Переключение вкладок кейсов и чата работает."""
    page.goto(BASE_URL)
    page.locator("#btn-load-test").click()
    expect(page.locator("#section-main")).to_be_visible(timeout=10000)

    # По умолчанию активна вкладка кейсов
    expect(page.locator("#tab-cases")).to_be_visible()

    # Переключаемся на чат
    page.locator(".tab-btn:has-text('чат')").click()
    expect(page.locator("#tab-chat")).to_be_visible()

    # Возвращаемся к кейсам
    page.locator(".tab-btn:has-text('кейс')").click()
    expect(page.locator("#tab-cases")).to_be_visible()


def test_case5_runs_and_shows_result(page: Page):
    """Запуск кейса 5 (не требует цели) показывает область результата."""
    page.goto(BASE_URL)
    page.locator("#btn-load-test").click()
    expect(page.locator("#section-main")).to_be_visible(timeout=10000)

    # Запускаем кейс 5 (не нужна цель)
    case_buttons = page.locator(".case-card .btn-primary").all()
    assert len(case_buttons) >= 5

    # Нажимаем кнопку 5-го кейса (индекс 4)
    case_buttons[4].click()

    # Ждём появления области результата
    expect(page.locator("#result-area")).to_be_visible(timeout=5000)
