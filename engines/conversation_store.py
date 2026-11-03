"""Small SQLite-backed store for bounded chat context."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class ConversationStore:
    def __init__(self, path: str | Path):
        self.path = str(path)

    def _connection(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("""CREATE TABLE IF NOT EXISTS conversation_turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_conversation_session ON conversation_turns(session_id, id)")
        return conn

    def append(self, session_id: str, role: str, content: str) -> None:
        if not session_id or role not in {"user", "assistant"} or not str(content).strip():
            return
        conn = self._connection()
        conn.execute("INSERT INTO conversation_turns(session_id, role, content) VALUES(?,?,?)",
                     (session_id, role, str(content).strip()[:12000]))
        conn.commit()
        conn.close()

    def recent(self, session_id: str, limit: int = 8) -> list[dict]:
        safe_limit = max(1, min(int(limit), 20))
        conn = self._connection()
        rows = conn.execute("""SELECT role, content, created_at FROM conversation_turns
            WHERE session_id=? ORDER BY id DESC LIMIT ?""", (session_id, safe_limit)).fetchall()
        conn.close()
        return [dict(row) for row in reversed(rows)]
