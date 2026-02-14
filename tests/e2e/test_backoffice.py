"""Playwright E2E тесты страницы бэк-офиса."""

import pytest
from playwright.sync_api import Page, expect


BASE_URL = "http://localhost:8000"


def test_backoffice_page_loads(page: Page):
    """Страница бэк-офиса загружается с корректным содержимым."""
    page.goto(f"{BASE_URL}/backoffice")
    # Проверяем что страница загрузилась (не 404)
    expect(page.locator("body")).to_be_visible()
    content = page.content()
    assert "Метрик" in content or "backoffice" in content.lower() or "Статистик" in content


def test_backoffice_has_stats_cards(page: Page):
    """Страница бэк-офиса содержит карточки со статистикой."""
    page.goto(f"{BASE_URL}/backoffice")
    # Ждём загрузки метрик
    page.wait_for_timeout(2000)
    expect(page.locator(".stat-card").first).to_be_visible()


def test_backoffice_has_ip_table(page: Page):
    """Страница бэк-офиса содержит таблицу IP или сообщение о пустых данных."""
    page.goto(f"{BASE_URL}/backoffice")
    page.wait_for_timeout(2000)

    ip_container = page.locator("#ip-table-container")
    expect(ip_container).to_be_visible()


def test_backoffice_has_cases_table(page: Page):
    """Страница бэк-офиса содержит таблицу кейсов с оценками."""
    page.goto(f"{BASE_URL}/backoffice")
    page.wait_for_timeout(2000)

    cases_container = page.locator("#cases-table-container")
    expect(cases_container).to_be_visible()


def test_backoffice_refresh_button_works(page: Page):
    """Кнопка обновления данных работает без ошибок."""
    page.goto(f"{BASE_URL}/backoffice")
    page.wait_for_timeout(1000)

    refresh_btn = page.locator(".refresh-btn")
    expect(refresh_btn).to_be_visible()
    refresh_btn.click()
    page.wait_for_timeout(2000)

    # После обновления страница всё ещё работает
    expect(page.locator(".stat-card").first).to_be_visible()


def test_backoffice_link_to_app(page: Page):
    """Ссылка из бэк-офиса на приложение работает."""
    page.goto(f"{BASE_URL}/backoffice")
    app_link = page.locator("a:has-text('Приложение')")
    expect(app_link).to_be_visible()
    href = app_link.get_attribute("href")
    assert href == "/" or "localhost" in (href or "")


def test_backoffice_shows_case_stats_for_all_7(page: Page):
    """После загрузки метрик отображаются строки для всех 7 кейсов."""
    page.goto(f"{BASE_URL}/backoffice")
    page.wait_for_timeout(3000)

    # Проверяем наличие таблицы кейсов
    cases_container = page.locator("#cases-table-container")
    content = cases_container.inner_text()

    # Все 7 кейсов должны присутствовать
    for i in range(1, 8):
        assert f"Кейс {i}" in content
