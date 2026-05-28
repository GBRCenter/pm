from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4

DB_PATH = Path(__file__).resolve().parent / "data" / "app.db"

INITIAL_BOARD_STATE: dict[str, Any] = {
    "version": 1,
    "columns": [
        {"id": "col-backlog", "title": "Backlog", "cardIds": ["card-1", "card-2"]},
        {"id": "col-discovery", "title": "Discovery", "cardIds": ["card-3"]},
        {
            "id": "col-progress",
            "title": "In Progress",
            "cardIds": ["card-4", "card-5"],
        },
        {"id": "col-review", "title": "Review", "cardIds": ["card-6"]},
        {"id": "col-done", "title": "Done", "cardIds": ["card-7", "card-8"]},
    ],
    "cards": {
        "card-1": {
            "id": "card-1",
            "title": "Align roadmap themes",
            "details": "Draft quarterly themes with impact statements and metrics.",
        },
        "card-2": {
            "id": "card-2",
            "title": "Gather customer signals",
            "details": "Review support tags, sales notes, and churn feedback.",
        },
        "card-3": {
            "id": "card-3",
            "title": "Prototype analytics view",
            "details": "Sketch initial dashboard layout and key drill-downs.",
        },
        "card-4": {
            "id": "card-4",
            "title": "Refine status language",
            "details": "Standardize column labels and tone across the board.",
        },
        "card-5": {
            "id": "card-5",
            "title": "Design card layout",
            "details": "Add hierarchy and spacing for scanning dense lists.",
        },
        "card-6": {
            "id": "card-6",
            "title": "QA micro-interactions",
            "details": "Verify hover, focus, and loading states.",
        },
        "card-7": {
            "id": "card-7",
            "title": "Ship marketing page",
            "details": "Final copy approved and asset pack delivered.",
        },
        "card-8": {
            "id": "card-8",
            "title": "Close onboarding sprint",
            "details": "Document release notes and share internally.",
        },
    },
}


@dataclass(frozen=True)
class UserRecord:
    id: str
    username: str


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    target = db_path or DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(db_path: Path | None = None) -> None:
    with _connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id TEXT PRIMARY KEY,
              username TEXT NOT NULL UNIQUE,
              password_hash TEXT NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS boards (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL UNIQUE,
              name TEXT NOT NULL DEFAULT 'My Board',
              state_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
              id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL,
              role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
              content TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_chat_messages_user_created_at
              ON chat_messages(user_id, created_at);
            """
        )

        user_id = _ensure_demo_user(connection)
        _ensure_demo_board(connection, user_id)


def _ensure_demo_user(connection: sqlite3.Connection) -> str:
    existing = connection.execute(
        "SELECT id FROM users WHERE username = ?",
        ("user",),
    ).fetchone()
    if existing:
        return str(existing["id"])

    user_id = _new_id("usr")
    connection.execute(
        "INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (user_id, "user", "password", _now_iso()),
    )
    return user_id


def _ensure_demo_board(connection: sqlite3.Connection, user_id: str) -> None:
    existing = connection.execute(
        "SELECT id FROM boards WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if existing:
        return

    board_id = _new_id("brd")
    now = _now_iso()
    connection.execute(
        (
            "INSERT INTO boards (id, user_id, name, state_json, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)"
        ),
        (board_id, user_id, "My Board", json.dumps(INITIAL_BOARD_STATE), now, now),
    )


def get_user_by_username(username: str, db_path: Path | None = None) -> UserRecord | None:
    with _connect(db_path) as connection:
        row = connection.execute(
            "SELECT id, username FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if not row:
            return None
        return UserRecord(id=str(row["id"]), username=str(row["username"]))


def verify_credentials(username: str, password: str, db_path: Path | None = None) -> bool:
    with _connect(db_path) as connection:
        row = connection.execute(
            "SELECT password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if not row:
            return False
        return str(row["password_hash"]) == password


def get_board_for_username(username: str, db_path: Path | None = None) -> dict[str, Any] | None:
    with _connect(db_path) as connection:
        row = connection.execute(
            (
                "SELECT b.state_json "
                "FROM boards b "
                "JOIN users u ON u.id = b.user_id "
                "WHERE u.username = ?"
            ),
            (username,),
        ).fetchone()
        if not row:
            return None
        return json.loads(str(row["state_json"]))


def save_board_for_username(
    username: str,
    board_state: dict[str, Any],
    db_path: Path | None = None,
) -> bool:
    with _connect(db_path) as connection:
        user_row = connection.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if not user_row:
            return False

        now = _now_iso()
        result = connection.execute(
            "UPDATE boards SET state_json = ?, updated_at = ? WHERE user_id = ?",
            (json.dumps(board_state), now, str(user_row["id"])),
        )
        return result.rowcount > 0
