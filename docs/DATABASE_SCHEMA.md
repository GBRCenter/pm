# Database schema proposal (Part 5)

## Goal

Define a simple SQLite schema for MVP that:
- supports multiple users,
- stores one Kanban board per user,
- stores board state as JSON,
- leaves a clear path for AI chat history in later parts.

DB file location:
- `backend/data/app.db`

---

## Tables

### 1) `users`

Purpose:
- Store users (MVP starts with one demo user, but schema supports many).

Columns:
- `id` TEXT PRIMARY KEY
- `username` TEXT NOT NULL UNIQUE
- `password_hash` TEXT NOT NULL
- `created_at` TEXT NOT NULL

Notes:
- Keep `password_hash` as field name even in MVP.
- Demo user is `user` and maps to current fake login behavior.

---

### 2) `boards`

Purpose:
- One board per user in MVP.

Columns:
- `id` TEXT PRIMARY KEY
- `user_id` TEXT NOT NULL UNIQUE
- `name` TEXT NOT NULL DEFAULT 'My Board'
- `state_json` TEXT NOT NULL
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

Constraints:
- `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE`
- `UNIQUE(user_id)` enforces exactly one board per user.

---

### 3) `chat_messages` (optional now, expected for Part 9)

Purpose:
- Persist conversation history per user.

Columns:
- `id` TEXT PRIMARY KEY
- `user_id` TEXT NOT NULL
- `role` TEXT NOT NULL
- `content` TEXT NOT NULL
- `created_at` TEXT NOT NULL

Constraints:
- `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE`
- `CHECK(role IN ('user', 'assistant', 'system'))`

Indexes:
- `idx_chat_messages_user_created_at` on `(user_id, created_at)`

---

## SQL DDL proposal

```sql
PRAGMA foreign_keys = ON;

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
```

---

## Board JSON shape (`boards.state_json`)

Versioned payload:

```json
{
  "version": 1,
  "columns": [
    { "id": "col-backlog", "title": "Backlog", "cardIds": ["card-1"] }
  ],
  "cards": {
    "card-1": {
      "id": "card-1",
      "title": "Example",
      "details": "Example details"
    }
  }
}
```

Rules:
- `version` required to support future migrations.
- `columns[*].cardIds` must reference existing keys in `cards`.
- Card IDs should appear in only one column.

---

## Initialization flow (when DB does not exist)

On backend startup:
1. Ensure folder exists: `backend/data/`.
2. Open/create SQLite file: `backend/data/app.db`.
3. Enable `PRAGMA foreign_keys = ON`.
4. Execute idempotent DDL (`CREATE TABLE IF NOT EXISTS ...`).
5. Seed demo user if missing (`username='user'`).
6. Seed demo board if missing for that user, using current Kanban initial JSON.

This keeps behavior deterministic and simple for MVP.

---

## Migration approach (simple MVP strategy)

- Start with lightweight startup migrations in code using ordered steps.
- Track schema version with `PRAGMA user_version`.
- For each new version:
  - apply SQL changes,
  - update `user_version`.

No external migration framework is required for MVP.

---

## Why this model

- Minimal schema, aligned with project simplicity rules.
- Fits current frontend data model (`columns` + `cards`).
- Ready for Part 6 API persistence and Part 9 chat context.
