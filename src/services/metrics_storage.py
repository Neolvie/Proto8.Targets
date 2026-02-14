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

        # Статистика по кейсам
        case_stats = []
        for case_id in range(1, 8):
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

        # Общий процент положительных оценок
        cursor.execute(
            "SELECT SUM(CASE WHEN vote = 1 THEN 1 ELSE 0 END) as pos, COUNT(*) as total FROM feedback"
        )
        fb_total = cursor.fetchone()
        pos_total = fb_total["pos"] or 0
        votes_total = fb_total["total"] or 0
        total_positive_pct = round(pos_total / votes_total * 100, 1) if votes_total > 0 else None

        return {
            "total_requests": total_requests,
            "unique_ips": unique_ips,
            "ip_stats": ip_stats,
            "case_stats": case_stats,
            "timeline": timeline,
            "total_positive_pct": total_positive_pct,
        }
    finally:
        conn.close()
