# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Kanban-based project management MVP. Next.js static frontend + Python FastAPI backend, deployed together in a single Docker container. The backend serves the compiled frontend as static files and exposes all API routes under `/api/`.

Login credentials are hardcoded: `user` / `password`.

## Commands

### Frontend (`frontend/`)

```bash
npm run dev          # dev server (Next.js)
npm run build        # static export → frontend/out/
npm run lint         # ESLint
npm run test         # Vitest unit tests (single run)
npm run test:unit:watch  # watch mode
npm run test:e2e     # Playwright e2e
```

Run a single test file:
```bash
npx vitest run src/lib/kanban.test.ts
```

### Backend (`backend/`)

```bash
uv run uvicorn main:app --reload   # dev server on port 8000
uv run pytest                      # all tests
uv run pytest tests/test_api.py    # single test file
```

Backend tests require no running server — they use an in-memory SQLite DB via `conftest.py`.

### Docker (production)

```bash
./scripts/start_mac.sh   # build image + start container on port 8000
./scripts/stop_mac.sh    # stop container
```

The Dockerfile copies `frontend/out/` to `backend/static/` in the final image.

## Architecture

### Board data model

```
{
  version: int,
  columns: [{ id, title, cardIds: string[] }],
  cards: { [id]: { id, title, details } }
}
```

Columns are fixed (cannot be added/deleted, only renamed). Cards are stored flat in the `cards` dict; their order within each column is determined by the `cardIds` arrays on the column objects.

### Backend modules

- `main.py` — FastAPI app, all routes, in-memory session management (`active_sessions` dict)
- `db.py` — SQLite access via stdlib `sqlite3`; database initialized at startup with a demo user and board
- `ai.py` — OpenRouter HTTP client + Pydantic models for AI operations (`CreateCardOperation`, `UpdateCardOperation`, `MoveCardOperation`, `DeleteCardOperation`, `RenameColumnOperation`)
- `board_ops.py` — Pure board mutation logic; `apply_operations()` deep-copies the board before applying AI-returned operations

Sessions are in-memory only and are lost on server restart.

The SQLite database defaults to `backend/data/app.db`. Override with `PM_DB_PATH` env var. Override the static files directory with `PM_STATIC_DIR`.

### AI chat flow

1. `POST /api/ai/chat` loads current board + last 10 chat messages from DB
2. Calls `run_board_chat()` which sends a JSON prompt to OpenRouter (`openai/gpt-oss-120b`)
3. AI returns `{ assistant_message, operations[] }`; operations are validated with Pydantic strict models
4. `apply_operations()` produces a new board state; both the board and the exchange are saved atomically

### Frontend modules

- `src/lib/kanban.ts` — Board types (`BoardData`, `Column`, `Card`) + pure `moveCard()` function for drag-and-drop logic
- `src/lib/api.ts` — Typed `fetch` wrappers for every API endpoint; throws `ApiError` on non-2xx
- `src/components/` — React components: `KanbanBoard`, `KanbanColumn`, `KanbanCard`, `AiChatSidebar`, etc.
- `src/app/page.tsx` — Root page; owns auth state

Drag-and-drop uses `@dnd-kit/core` and `@dnd-kit/sortable`. The drag state is computed locally by `moveCard()` on every `onDragOver` event; the final position is persisted to the backend on `onDragEnd`.

## Environment

`.env` at project root is required for AI features:
```
OPENROUTER_API_KEY=...
```

## Color scheme

- Accent Yellow: `#ecad0a`
- Blue Primary: `#209dd7`
- Purple Secondary: `#753991`
- Dark Navy: `#032147`
- Gray Text: `#888888`

## Coding standards

- No over-engineering; no unnecessary defensive programming; no extra features
- Identify root cause before attempting a fix — prove with evidence
- No emojis anywhere in code or output
