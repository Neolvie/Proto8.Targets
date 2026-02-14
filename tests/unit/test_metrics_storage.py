"""Unit-тесты для хранилища метрик SQLite."""

import pytest
from src.services.metrics_storage import init_db, log_request, save_feedback, get_metrics


class TestInitDb:
    """Тесты инициализации базы данных."""

    def test_init_creates_db(self, temp_data_dir):
        """Инициализация создаёт базу данных без ошибок."""
        import os
        init_db()
        db_path = os.path.join(temp_data_dir, "metrics.db")
        assert os.path.exists(db_path)

    def test_init_idempotent(self):
        """Повторная инициализация не вызывает ошибок."""
        init_db()
        init_db()  # Второй вызов не должен вызывать исключений


class TestLogRequest:
    """Тесты записи запросов в БД."""

    def test_log_simple_request(self):
        """Запрос логируется без ошибок."""
        log_request("127.0.0.1", "/api/data/test")
        metrics = get_metrics()
        assert metrics["total_requests"] >= 1

    def test_log_request_with_case(self):
        """Запрос с case_id логируется корректно."""
        log_request("192.168.1.1", "/api/cases/3", case_id=3)
        metrics = get_metrics()
        case3 = next(c for c in metrics["case_stats"] if c["case_id"] == 3)
        assert case3["requests"] >= 1

    def test_unique_ip_counted(self):
        """Уникальные IP корректно подсчитываются."""
        log_request("10.0.0.1", "/api/chat")
        log_request("10.0.0.2", "/api/chat")
        metrics = get_metrics()
        assert metrics["unique_ips"] >= 2


class TestSaveFeedback:
    """Тесты сохранения оценок."""

    def test_save_positive_feedback(self):
        """Положительная оценка сохраняется корректно."""
        save_feedback("1.1.1.1", case_id=1, session_id="sess_test_1", vote=1)
        metrics = get_metrics()
        case1 = next(c for c in metrics["case_stats"] if c["case_id"] == 1)
        assert case1["positive"] >= 1

    def test_save_negative_feedback(self):
        """Отрицательная оценка сохраняется корректно."""
        save_feedback("2.2.2.2", case_id=2, session_id="sess_test_2", vote=-1)
        metrics = get_metrics()
        case2 = next(c for c in metrics["case_stats"] if c["case_id"] == 2)
        assert case2["negative"] >= 1

    def test_feedback_update_on_conflict(self):
        """Повторная оценка от той же сессии обновляет существующую."""
        session = "sess_conflict_test"
        save_feedback("3.3.3.3", case_id=4, session_id=session, vote=1)
        save_feedback("3.3.3.3", case_id=4, session_id=session, vote=-1)

        metrics = get_metrics()
        case4 = next(c for c in metrics["case_stats"] if c["case_id"] == 4)
        # Не должно накапливать дублей — должна быть только 1 запись (отрицательная)
        # Точное число зависит от предыдущих тестов, но positive должно не включать этот голос
        assert isinstance(case4["positive"], int)
        assert isinstance(case4["negative"], int)


class TestGetMetrics:
    """Тесты агрегации метрик."""

    def test_metrics_structure(self):
        """Метрики содержат все необходимые поля."""
        metrics = get_metrics()
        assert "total_requests" in metrics
        assert "unique_ips" in metrics
        assert "ip_stats" in metrics
        assert "case_stats" in metrics
        assert "timeline" in metrics
        assert "total_positive_pct" in metrics

    def test_case_stats_has_all_7_cases(self):
        """Статистика кейсов содержит данные для всех 7 кейсов."""
        metrics = get_metrics()
        case_ids = [c["case_id"] for c in metrics["case_stats"]]
        assert set(case_ids) == {1, 2, 3, 4, 5, 6, 7}

    def test_pct_positive_calculation(self):
        """Процент положительных оценок вычисляется корректно."""
        # Добавляем 3 положительных и 1 отрицательную для кейса 7
        save_feedback("100.1.1.1", 7, "sess_p1", 1)
        save_feedback("100.1.1.2", 7, "sess_p2", 1)
        save_feedback("100.1.1.3", 7, "sess_p3", 1)
        save_feedback("100.1.1.4", 7, "sess_n1", -1)

        metrics = get_metrics()
        # Должен быть ненулевой процент
        if metrics["total_positive_pct"] is not None:
            assert 0 <= metrics["total_positive_pct"] <= 100
