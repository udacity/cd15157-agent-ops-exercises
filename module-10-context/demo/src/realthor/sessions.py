"""The application database: users and sessions (demo).

Distinct from the checkpointer (``state.db``, agent state). This is *application*
state: who the users are and the resumable conversations they own. A user lists
and resumes only their own sessions — ownership is the query's WHERE clause.
"""

import sqlite3
import uuid
from datetime import datetime, timezone

import pandas as pd

USERS_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id       TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    role          TEXT NOT NULL,
    region_access TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    active        INTEGER NOT NULL DEFAULT 1
)
"""

SESSIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id     TEXT PRIMARY KEY,
    user_id        TEXT NOT NULL,
    title          TEXT NOT NULL,
    created_at     TEXT NOT NULL,
    last_active_at TEXT NOT NULL,
    message_count  INTEGER NOT NULL DEFAULT 0
)
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(app_db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(app_db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(app_db_path: str) -> None:
    conn = connect(app_db_path)
    try:
        conn.execute(USERS_SCHEMA)
        conn.execute(SESSIONS_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def seed_users_from_csv(app_db_path: str, users_csv: str, password_hash: str) -> int:
    init_db(app_db_path)
    df = pd.read_csv(users_csv)
    conn = connect(app_db_path)
    try:
        for _, r in df.iterrows():
            conn.execute(
                "INSERT OR REPLACE INTO users "
                "(user_id, name, role, region_access, password_hash, active) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (str(r["user_id"]), str(r["name"]), str(r["role"]),
                 str(r["region_access"]), password_hash, 1 if bool(r["active"]) else 0),
            )
        conn.commit()
    finally:
        conn.close()
    return len(df)


def is_empty(app_db_path: str) -> bool:
    init_db(app_db_path)
    conn = connect(app_db_path)
    try:
        return conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"] == 0
    finally:
        conn.close()


def get_user(app_db_path: str, user_id: str):
    conn = connect(app_db_path)
    try:
        return conn.execute(
            "SELECT * FROM users WHERE user_id = ? AND active = 1", (user_id,)
        ).fetchone()
    finally:
        conn.close()


def create_session(app_db_path: str, user_id: str, title: str) -> str:
    session_id = str(uuid.uuid4())
    now = _now()
    conn = connect(app_db_path)
    try:
        conn.execute(
            "INSERT INTO sessions "
            "(session_id, user_id, title, created_at, last_active_at, message_count) "
            "VALUES (?, ?, ?, ?, ?, 0)",
            (session_id, user_id, title, now, now),
        )
        conn.commit()
    finally:
        conn.close()
    return session_id


def list_sessions(app_db_path: str, user_id: str) -> list[dict]:
    """A user's own sessions, most recently active first (ownership = WHERE)."""
    conn = connect(app_db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM sessions WHERE user_id = ? ORDER BY last_active_at DESC",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def get_session(app_db_path: str, session_id: str, user_id: str) -> dict | None:
    """Fetch a session only if ``user_id`` owns it — else None (ownership check)."""
    conn = connect(app_db_path)
    try:
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ? AND user_id = ?",
            (session_id, user_id),
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def touch_session(app_db_path: str, session_id: str) -> None:
    conn = connect(app_db_path)
    try:
        conn.execute(
            "UPDATE sessions SET last_active_at = ?, message_count = message_count + 1 "
            "WHERE session_id = ?",
            (_now(), session_id),
        )
        conn.commit()
    finally:
        conn.close()


def generate_title(first_message: str, max_len: int = 40) -> str:
    """A human-readable title from the first message (prefix strategy for the demo)."""
    text = " ".join(first_message.split())
    if len(text) <= max_len:
        return text or "New session"
    return text[:max_len].rstrip() + "…"
