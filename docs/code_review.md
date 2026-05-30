# Code Review

Reviewed commit `c292ef9` (branch `mario/parts-2-4`). All 48 tests pass. The codebase is clean and well-structured for an MVP. Findings are ordered by severity.

---

## High — Functional gaps or correctness issues

### 1. Chat history is lost on page refresh

**File:** `frontend/src/components/AiChatSidebar.tsx:7`

`messages` is local React state, initialized as `[]`. On every page load the sidebar shows "No messages yet", even though the backend persists the last 10 exchanges in `chat_messages` and already returns them as context to the AI.

There is no `GET /api/ai/chat/history` endpoint and no call to load history on mount.

**Action:** Add a `GET /api/ai/chat/history` backend endpoint that returns the last N messages for the authenticated user. Call it from `AiChatSidebar` in a `useEffect` on mount, mirroring how `KanbanBoard` loads the board.

---

### 2. Passwords stored in plain text

**File:** `backend/db.py:193`

```python
return str(row["password_hash"]) == password
```

The column is named `password_hash` but contains the literal string `"password"` with no hashing. Even for a local MVP, this is one `import hashlib` away from being correct and sets a bad precedent if the codebase evolves.

**Action:** Hash with `hashlib.sha256(password.encode()).hexdigest()` on write and the same on comparison. Migrate the seed user record in `_ensure_demo_user`.

---

### 3. Sessions never expire

**File:** `backend/main.py:56`

`active_sessions: dict[str, str] = {}` — sessions are in-memory, lost on restart, and have no TTL. A token issued today is valid indefinitely until the process stops.

**Action:** Store a creation timestamp alongside each token and reject tokens older than a configurable TTL (e.g., 24 h) in `_get_authenticated_username`.

---

## Medium — Code correctness / test health

### 4. `board.cards[cardId]` can silently yield `undefined`

**File:** `frontend/src/components/KanbanBoard.tsx:308`

```tsx
cards={column.cardIds.map((cardId) => board.cards[cardId])}
```

`board.cards` is typed `Record<string, Card>`, so TypeScript allows indexing with any string and infers `Card` (not `Card | undefined`). If the board state is ever inconsistent (e.g., a partial write during an AI operation error), this passes `undefined` into `KanbanCard`'s `card` prop, causing a runtime crash.

**Action:** Type `cards` as `Record<string, Card | undefined>` or filter out missing entries: `.map((id) => board.cards[id]).filter((c): c is Card => c != null)`.

---

### 5. `handleRenameColumn` re-throws after reverting state

**File:** `frontend/src/components/KanbanBoard.tsx:162`

```ts
} catch (error) {
  setBoard(previousBoard);
  setErrorMessage("Could not rename the column.");
  throw error;  // ← unnecessary
}
```

`KanbanColumn.tsx:47–51` catches this throw silently and resets `draftTitle` — but `draftTitle` is already reset via the `column.title` prop update from `setBoard(previousBoard)` in the parent. The `throw error` adds no benefit and creates an unhandled rejection if the caller doesn't catch it.

**Action:** Remove the `throw error`. The board-level error message is sufficient.

---

### 6. `_columnId` is vestigial in the delete callback chain

**File:** `frontend/src/components/KanbanBoard.tsx:189`

```ts
const handleDeleteCard = (_columnId: string, cardId: string) => {
```

`_columnId` is passed from `KanbanColumn` but never used. The backend only needs `cardId` for deletion. Passing column ID through the callback adds noise.

**Action:** Remove `_columnId` from `handleDeleteCard` and update the call site in `KanbanColumn.tsx` (`onDelete={(cardId) => onDeleteCard(cardId)}`).

---

### 7. `httpx` / `starlette.testclient` deprecation warning

**File:** `backend/pyproject.toml`

```
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated;
install `httpx2` instead.
```

This warning fires on every test run and will become a hard error in a future FastAPI/Starlette release.

**Action:** Add `httpx2>=0.1` to `[dependency-groups] dev` and remove the plain `httpx` dev dependency (keep it in `dependencies` only if needed at runtime — it is, for `ai.py`).

---

### 8. No `onDragOver` handler — no live reorder preview

**File:** `frontend/src/components/KanbanBoard.tsx:297`

Cards only reorder visually on `onDragEnd`. During a drag across columns or within a column, the placeholder stays in the original position. The `DragOverlay` shows the dragged card floating correctly, but the destination slot is not previewed.

**Action:** Add an `onDragOver` handler that calls `moveCard` and does `setBoard({ ...board, columns: nextColumns })` on the optimistic local state (without persisting), then let `onDragEnd` persist the final placement as it already does.

---

## Low — Minor improvements

### 9. Model name is not configurable

**File:** `backend/ai.py:19`

```python
OPENROUTER_MODEL = "openai/gpt-oss-120b"
```

Switching models requires a code change and rebuild.

**Action:** Read from `os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b")` so it can be overridden via `.env` or Docker `--env`.

---

### 10. Chat input does not auto-scroll to newest message

**File:** `frontend/src/components/AiChatSidebar.tsx:83`

The `role="log"` div has `overflow-y-auto` but no scroll-to-bottom logic. After several exchanges, new messages appear off-screen.

**Action:** Add a `ref` to the message container and a `useEffect` that calls `ref.current.scrollTop = ref.current.scrollHeight` whenever `messages` changes.

---

### 11. `_db_path()` is called on every request

**File:** `backend/main.py:31–35`

`_db_path()` calls `os.getenv("PM_DB_PATH")` on every route invocation. `os.getenv` is fast, but the value never changes after startup.

**Action:** Resolve once in the `lifespan` handler and store the result in a module-level variable, eliminating repeated env lookups.

---

## Summary table

| # | Severity | File | Description |
|---|----------|------|-------------|
| 1 | High | `AiChatSidebar.tsx` | Chat history lost on refresh — no load-on-mount call |
| 2 | High | `db.py:193` | Plain-text password comparison despite `_hash` field name |
| 3 | High | `main.py:56` | Sessions never expire |
| 4 | Medium | `KanbanBoard.tsx:308` | `board.cards[cardId]` can be `undefined` — silent crash risk |
| 5 | Medium | `KanbanBoard.tsx:162` | `throw error` in rename catch is redundant |
| 6 | Medium | `KanbanBoard.tsx:189` | `_columnId` vestigial in delete callback |
| 7 | Medium | `pyproject.toml` | `httpx`/`starlette` deprecation warning in tests |
| 8 | Medium | `KanbanBoard.tsx:297` | No live reorder preview during drag |
| 9 | Low | `ai.py:19` | Model name hardcoded, not env-configurable |
| 10 | Low | `AiChatSidebar.tsx:83` | Chat panel does not scroll to newest message |
| 11 | Low | `main.py:31` | `_db_path()` resolves env var on every request |
