"""SQLite хранилище метрик использования и обратной связи."""

import sqlite3
import os
from datetime import datetime, timezone
from typing import Optional
from src.config import get_data_dir


def _get_db_path() -> str:
    """Возвращает путь к файлу базы данных SQLite."""
    data_dir = get_data_dir()
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "metrics.db")


def init_db() -> None:
    """
    Инициализирует базу данных SQLite: создаёт таблицы если они не существуют.

    Создаёт таблицы:
    - requests: журнал запросов к API
    - feedback: оценки пользователей (👍/👎)
    """
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                case_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT NOT NULL,
                case_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                vote INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(case_id, session_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT NOT NULL,
                session_id TEXT NOT NULL,
                vote INTEGER NOT NULL,
                user_message TEXT NOT NULL,
                summary TEXT,
                context_type TEXT NOT NULL,
                context_name TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Миграция: добавить summary если таблица уже существовала без неё
        try:
            cursor.execute("ALTER TABLE chat_feedback ADD COLUMN summary TEXT")
        except Exception:
            pass  # колонка уже есть
        conn.commit()
    finally:
        conn.close()


def log_request(ip: str, endpoint: str, case_id: Optional[int] = None) -> None:
    """
    Записывает запрос к API в базу данных.

    Args:
        ip: IP-адрес пользователя.
        endpoint: Путь запроса (например /api/cases/1).
        case_id: ID кейса если запрос относится к кейсу.
    """
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO requests (ip, endpoint, case_id, timestamp) VALUES (?, ?, ?, ?)",
            (ip, endpoint, case_id, datetime.now(timezone.utc).isoformat())
        )
        conn.commit()
    finally:
        conn.close()


def save_feedback(ip: str, case_id: int, session_id: str, vote: int) -> None:
    """
    Сохраняет оценку пользователя (👍/👎) для конкретного кейса и сессии.

    При повторной оценке в рамках той же сессии обновляет существующую запись.

    Args:
        ip: IP-адрес пользователя.
        case_id: ID кейса (1-7).
        session_id: Уникальный идентификатор сессии браузера.
        vote: 1 для 👍, -1 для 👎.
    """
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            INSERT INTO feedback (ip, case_id, session_id, vote, timestamp)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(case_id, session_id) DO UPDATE SET
                vote = excluded.vote,
                ip = excluded.ip,
                timestamp = excluded.timestamp
        """, (ip, case_id, session_id, vote, datetime.now(timezone.utc).isoformat()))
        conn.commit()
    finally:
        conn.close()


def save_chat_feedback(
    ip: str,
    session_id: str,
    vote: int,
    user_message: str,
    context_type: str,
    context_name: str,
) -> int:
    """
    Сохраняет оценку ответа свободного чата.

    Args:
        ip: IP-адрес пользователя.
        session_id: Уникальный идентификатор сессии браузера.
        vote: 1 для 👍, -1 для 👎.
        user_message: Полный текст вопроса пользователя.
        context_type: Тип контекста ('map' или 'target').
        context_name: Название карты или цели.

    Returns:
        int: ID вставленной записи (для последующего обновления summary).
    """
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.execute(
            """
            INSERT INTO chat_feedback
                (ip, session_id, vote, user_message, context_type, context_name, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ip, session_id, vote, user_message,
                context_type, context_name,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def update_chat_feedback_summary(feedback_id: int, summary: str) -> None:
    """
    Обновляет краткое резюме запроса пользователя для записи чат-фидбека.

    Args:
        feedback_id: ID записи в chat_feedback.
        summary: Краткое резюме (2-3 слова) от LLM.
    """
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "UPDATE chat_feedback SET summary = ? WHERE id = ?",
            (summary, feedback_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_metrics() -> dict:
    """
    Возвращает агрегированные метрики использования для бэк-офиса.

    Returns:
        dict: Словарь с метриками:
            - total_requests: общее количество запросов
            - unique_ips: количество уникальных IP
            - ip_stats: список [{ip, count}] по убыванию
            - case_stats: [{case_id, requests, positive, negative, pct_positive}]
            - timeline: [{date, count}] за последние 30 дней
            - total_positive_pct: общий процент положительных оценок
    """
    db_path = _get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()

        # Общая статистика
        cursor.execute("SELECT COUNT(*) as cnt, COUNT(DISTINCT ip) as uniq FROM requests")
        row = cursor.fetchone()
        total_requests = row["cnt"] if row else 0
        unique_ips = row["uniq"] if row else 0

        # Статистика по IP
        cursor.execute("""
            SELECT ip, COUNT(*) as cnt
            FROM requests
            GROUP BY ip
            ORDER BY cnt DESC
            LIMIT 20
        """)
        ip_stats = [{"ip": r["ip"], "count": r["cnt"]} for r in cursor.fetchall()]

        # Статистика по кейсам (кейс 4 удалён)
        case_stats = []
        for case_id in [1, 2, 3, 5, 6, 7]:
            cursor.execute(
                "SELECT COUNT(*) as cnt FROM requests WHERE case_id = ?",
                (case_id,)
            )
            req_count = cursor.fetchone()["cnt"]

            cursor.execute(
                "SELECT SUM(CASE WHEN vote = 1 THEN 1 ELSE 0 END) as pos, "
                "SUM(CASE WHEN vote = -1 THEN 1 ELSE 0 END) as neg "
                "FROM feedback WHERE case_id = ?",
                (case_id,)
            )
            fb = cursor.fetchone()
            positive = fb["pos"] or 0
            negative = fb["neg"] or 0
            total_votes = positive + negative
            pct = round(positive / total_votes * 100, 1) if total_votes > 0 else None

            case_stats.append({
                "case_id": case_id,
                "requests": req_count,
                "positive": positive,
                "negative": negative,
                "pct_positive": pct,
            })

        # График по дням (последние 30 дней)
        cursor.execute("""
            SELECT DATE(timestamp) as date, COUNT(*) as cnt
            FROM requests
            WHERE timestamp >= DATE('now', '-30 days')
            GROUP BY DATE(timestamp)
            ORDER BY date
        """)
        timeline = [{"date": r["date"], "count": r["cnt"]} for r in cursor.fetchall()]

        # Общий процент положительных оценок (кейсы)
        cursor.execute(
            "SELECT SUM(CASE WHEN vote = 1 THEN 1 ELSE 0 END) as pos, COUNT(*) as total FROM feedback"
        )
        fb_total = cursor.fetchone()
        pos_total = fb_total["pos"] or 0
        votes_total = fb_total["total"] or 0
        total_positive_pct = round(pos_total / votes_total * 100, 1) if votes_total > 0 else None

        # Оценки свободного чата (последние 50 записей для бэкофиса)
        cursor.execute("""
            SELECT id, timestamp, vote, context_type, context_name, user_message, summary
            FROM chat_feedback
            ORDER BY id DESC
            LIMIT 50
        """)
        chat_feedback_rows = [
            {
                "id": r["id"],
                "timestamp": r["timestamp"],
                "vote": r["vote"],
                "context_type": r["context_type"],
                "context_name": r["context_name"],
                "user_message": r["user_message"],
                "summary": r["summary"],
            }
            for r in cursor.fetchall()
        ]

        # Сводка по чат-оценкам
        cursor.execute(
            "SELECT SUM(CASE WHEN vote=1 THEN 1 ELSE 0 END) as pos, COUNT(*) as total FROM chat_feedback"
        )
        cf = cursor.fetchone()
        chat_pos = cf["pos"] or 0
        chat_total = cf["total"] or 0
        chat_positive_pct = round(chat_pos / chat_total * 100, 1) if chat_total > 0 else None

        return {
            "total_requests": total_requests,
            "unique_ips": unique_ips,
            "ip_stats": ip_stats,
            "case_stats": case_stats,
            "timeline": timeline,
            "total_positive_pct": total_positive_pct,
            "chat_feedback": chat_feedback_rows,
            "chat_positive_pct": chat_positive_pct,
            "chat_total_votes": chat_total,
        }
    finally:
        conn.close()
