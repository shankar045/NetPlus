import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "netpulse.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS monitoring_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                host TEXT NOT NULL,
                port INTEGER NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('UP', 'DOWN')),
                latency_ms REAL,
                message TEXT NOT NULL,
                alert TEXT,
                checked_at TEXT NOT NULL
            )
        """)
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_results_checked_at
            ON monitoring_results(checked_at DESC)
        """)


def save_result(result):
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO monitoring_results
                (name, host, port, status, latency_ms, message, alert, checked_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result["name"], result["host"], result["port"], result["status"],
            result["latency_ms"], result["message"], result.get("alert"),
            result["checked_at"],
        ))


def get_history(limit=30):
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT id, name, host, port, status, latency_ms, message, alert, checked_at
            FROM monitoring_results
            ORDER BY id DESC LIMIT ?
        """, (limit,)).fetchall()
    return [dict(row) for row in reversed(rows)]


def get_summary():
    with get_connection() as connection:
        total = connection.execute(
            "SELECT COUNT(*) AS n FROM monitoring_results"
        ).fetchone()["n"]
        up = connection.execute(
            "SELECT COUNT(*) AS n FROM monitoring_results WHERE status='UP'"
        ).fetchone()["n"]
        down = connection.execute(
            "SELECT COUNT(*) AS n FROM monitoring_results WHERE status='DOWN'"
        ).fetchone()["n"]
        avg_latency = connection.execute(
            "SELECT AVG(latency_ms) AS avg FROM monitoring_results WHERE status='UP'"
        ).fetchone()["avg"]
        distinct_hosts = connection.execute(
            "SELECT COUNT(DISTINCT host || ':' || port) AS n FROM monitoring_results"
        ).fetchone()["n"]

    return {
        "total_checks": total,
        "successful_checks": up,
        "failed_checks": down,
        "average_latency_ms": round(avg_latency, 2) if avg_latency is not None else None,
        "hosts_tested": distinct_hosts,
    }


def get_recent_alerts(limit=10):
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT name, host, port, status, latency_ms, alert, checked_at
            FROM monitoring_results
            WHERE alert IS NOT NULL AND alert != ''
            ORDER BY id DESC LIMIT ?
        """, (limit,)).fetchall()
    return [dict(row) for row in rows]
