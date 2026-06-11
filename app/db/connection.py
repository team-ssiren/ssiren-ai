"""SQLite connection factory (stdlib sqlite3).

A single process-wide connection is opened lazily and reused. sqlite calls are
blocking, so async callers MUST wrap repository functions in ``run_in_threadpool``.
The connection is read-mostly at request time; only ingestion writes.
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from app.config import get_settings

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")

_conn: sqlite3.Connection | None = None
_lock = threading.Lock()


def _connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_connection() -> sqlite3.Connection:
    """Return the shared connection, creating + initializing the schema on first use."""
    global _conn
    if _conn is None:
        with _lock:
            if _conn is None:
                conn = _connect(get_settings().sqlite_db_path)
                _run_schema(conn)
                _conn = conn
    return _conn


def _run_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def run_schema() -> None:
    """Ensure the DB file + tables exist (idempotent). Called from app lifespan."""
    _run_schema(get_connection())


def reset_connection_for_tests() -> None:
    """Drop the cached connection so tests can repoint sqlite_db_path."""
    global _conn
    with _lock:
        if _conn is not None:
            _conn.close()
        _conn = None
