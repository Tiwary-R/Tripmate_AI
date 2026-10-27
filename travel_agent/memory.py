"""Memory for the ADK orchestrator: a free/local SQLite preference store + an ADK session-service factory.

Replaces the previous LangGraph checkpointer/store. No LangGraph dependency.
- Conversation/run state is held in an ADK SessionService (see orchestrator.py).
- Long-term user preferences persist in a small SQLite file (works offline, no Postgres needed).
"""

import json
import os
import sqlite3
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
PREF_DB_PATH = Path(os.getenv("PREF_DB_PATH", _ROOT / "preferences.db"))
MEMORY_DB_PATH = Path(os.getenv("MEMORY_DB_PATH", _ROOT / "memory.db"))
SCORES_DB_PATH = Path(os.getenv("SCORES_DB_PATH", _ROOT / "scores.db"))
SESSION_DB_PATH = _ROOT / "adk_sessions.db"


class _Item:
    """Mimics the LangGraph store item interface the supervisor expects (`.value` dict)."""

    def __init__(self, value: dict):
        self.value = value


class PreferenceStore:
    """Tiny namespaced key-value store backed by SQLite. Interface matches what supervisor_node uses:
    get(namespace, key) -> _Item | None, put(namespace, key, value_dict), delete(namespace, key)."""

    def __init__(self, db_path: Path = PREF_DB_PATH):
        self.db_path = Path(db_path)
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS prefs (ns TEXT, key TEXT, value TEXT, PRIMARY KEY (ns, key))"
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    @staticmethod
    def _ns(namespace) -> str:
        return "/".join(namespace) if isinstance(namespace, (tuple, list)) else str(namespace)

    def get(self, namespace, key: str) -> _Item | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM prefs WHERE ns = ? AND key = ?", (self._ns(namespace), key)
            ).fetchone()
        return _Item(json.loads(row[0])) if row else None

    def put(self, namespace, key: str, value: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO prefs (ns, key, value) VALUES (?, ?, ?) "
                "ON CONFLICT(ns, key) DO UPDATE SET value = excluded.value",
                (self._ns(namespace), key, json.dumps(value)),
            )

    def delete(self, namespace, key: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM prefs WHERE ns = ? AND key = ?", (self._ns(namespace), key))


class MemoryStore:
    """Durable long-term memory of past trips/conversations, per user (SQLite, free/local).

    The orchestrator saves a one-line memory after each completed plan and recalls recent ones at the start
    of the next request, so the agent 'remembers' what a user has planned before.
    """

    def __init__(self, db_path: Path = MEMORY_DB_PATH):
        self.db_path = Path(db_path)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS memories "
                "(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, ts TEXT, text TEXT)"
            )

    def add(self, user_id: str, text: str) -> None:
        from datetime import datetime, timezone

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO memories (user_id, ts, text) VALUES (?, ?, ?)",
                (user_id, datetime.now(timezone.utc).isoformat(), text),
            )

    def recent(self, user_id: str, limit: int = 5) -> list[str]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT text FROM memories WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit)
            ).fetchall()
        return [r[0] for r in rows]


class ScoreLog:
    """Durable log of each run's evaluation score, per user (SQLite), for a quality trend."""

    def __init__(self, db_path: Path = SCORES_DB_PATH):
        self.db_path = Path(db_path)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS scores "
                "(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, ts TEXT, dest TEXT, score INTEGER, grade TEXT)"
            )

    def add(self, user_id: str, dest: str, score: int, grade: str) -> None:
        from datetime import datetime, timezone

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO scores (user_id, ts, dest, score, grade) VALUES (?, ?, ?, ?, ?)",
                (user_id, datetime.now(timezone.utc).isoformat(), dest or "", int(score), grade or ""),
            )

    def recent(self, user_id: str, limit: int = 20) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT ts, dest, score, grade FROM scores WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        return [{"ts": r[0], "dest": r[1], "score": r[2], "grade": r[3]} for r in reversed(rows)]


def make_session_service():
    """Return (session_service, backend_label). Durable SQLite sessions by default (free/local, survive
    restart). Override the URL with ADK_SQLITE_SESSIONS; falls back to in-memory if the DB can't be opened.
    """
    url = os.getenv("ADK_SQLITE_SESSIONS", "").strip()
    if not url:
        url = f"sqlite+aiosqlite:///{SESSION_DB_PATH.as_posix()}"
    elif url.startswith("sqlite:///"):  # upgrade a sync URL to the async driver ADK requires
        url = url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    try:
        from google.adk.sessions import DatabaseSessionService

        return DatabaseSessionService(db_url=url), "adk-sqlite"
    except Exception:
        from google.adk.sessions import InMemorySessionService

        return InMemorySessionService(), "adk-memory"


def close_memory() -> None:
    """Kept for CLI/FastAPI compatibility. No persistent pool to close."""
    return None
