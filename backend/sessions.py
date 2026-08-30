import sqlite3
import os
from datetime import datetime

DB_PATH = os.getenv("SESSION_DB", "/data/sessions.db")


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, title TEXT, created_at TEXT)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT, content TEXT, created_at TEXT)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)"
        )


def create_session(session_id: str, title: str | None = None):
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO sessions (id, title, created_at) VALUES (?, ?, ?)",
            (session_id, title or "Untitled", datetime.utcnow().isoformat()),
        )


def list_sessions() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute("SELECT id, title, created_at FROM sessions ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def get_session(session_id: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT id, title, created_at FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return dict(row) if row else None


def rename_session(session_id: str, title: str):
    with _conn() as conn:
        conn.execute("UPDATE sessions SET title = ? WHERE id = ?", (title, session_id))


def delete_session(session_id: str):
    with _conn() as conn:
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))


def add_message(session_id: str, role: str, content: str):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, datetime.utcnow().isoformat()),
        )


def get_messages(session_id: str) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, session_id, role, content, created_at FROM messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]
