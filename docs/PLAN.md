# Project Plan (Detailed Checklist)

## Agreed constraints and decisions

- [x] Keep implementation simple (MVP, no over-engineering).
- [x] Fake login for MVP: username `user`, password `password`.
- [x] Session approach: simple session (cookie/session token), no advanced auth hardening for now.
- [x] SQLite file path: `backend/data/app.db`.
- [x] AI provider: OpenRouter (`OPENROUTER_API_KEY` from root `.env`).
- [x] AI model target: `openai/gpt-oss-120b`.

## Part 1: Plan and baseline documentation

### Objective
Create an executable delivery plan and document the current frontend baseline.

### Checklist
- [x] Expand this file with detailed steps, tests, and success criteria for Parts 2–10.
- [x] Create `frontend/AGENTS.md` describing current frontend structure and behavior.
- [x] Add approval checkpoints before major irreversible work.

### Tests
- [x] `docs/PLAN.md` includes actionable checklists for every part.
- [x] `frontend/AGENTS.md` exists and matches current codebase reality.

### Success criteria
- [x] Plan is approved by user before implementation continues.

---

## Part 2: Scaffolding (Docker + FastAPI + scripts)

### Objective
Create a runnable local containerized backend with a hello-world page and one API endpoint.

### Checklist
- [x] Create FastAPI app scaffold in `backend/`.
- [x] Add health endpoint (`/api/health`) and hello page (`/`).
- [x] Add Dockerfile for unified app container.
- [x] Add runtime dependencies with `uv` flow in container.
- [x] Create cross-platform scripts in `scripts/`:
	- [x] `start_mac.sh`, `stop_mac.sh`
	- [x] `start_linux.sh`, `stop_linux.sh`
	- [x] `start_windows.bat` or `.ps1`, `stop_windows.bat` or `.ps1`
- [x] Ensure scripts are minimal and documented.

### Tests
- [x] Container builds successfully.
- [x] Running start script serves `/` and `/api/health`.
- [x] Stop script cleanly shuts down stack.

### Success criteria
- [x] Local Docker run works from scripts on at least macOS path.
- [x] API health route returns 200 and expected JSON.

### Approval checkpoint
- [x] User approves scaffolding before frontend integration.

---

## Part 3: Serve existing frontend statically from backend

### Objective
Build current Next.js frontend as static assets and serve at `/` via FastAPI.

### Checklist
- [x] Configure frontend static build output.
- [x] Add backend static file mounting.
- [x] Ensure root route serves frontend app shell.
- [x] Keep existing Kanban behavior unchanged.

### Tests
- [x] Frontend unit tests pass.
- [x] E2E smoke test loads board via backend-served URL.
- [x] Static assets (JS/CSS) resolve correctly from backend.

### Success criteria
- [x] App opens at `/` and displays existing Kanban demo with 5 columns.

---

## Part 4: Fake sign-in flow

### Objective
Require login before board access with simple session handling.

### Checklist
- [x] Add login UI screen and logout action.
- [x] Add backend auth endpoints for login/logout/session check.
- [x] Enforce route guard so unauthenticated users cannot access board data.
- [x] Use simple session mechanism only (MVP level).

### Tests
- [x] Valid credentials (`user` / `password`) allow login.
- [x] Invalid credentials rejected.
- [x] Logout invalidates session.
- [x] Refresh preserves session while valid.

### Success criteria
- [x] User must log in to see and use board.

### Approval checkpoint
- [x] User approves fake-auth UX before database persistence.

---

## Part 5: Database modeling (JSON-based board state)

### Objective
Define SQLite schema that supports multiple users and one board per user for MVP.

### Proposed schema (for approval)

- `users`
	- `id` (TEXT PK)
	- `username` (TEXT UNIQUE NOT NULL)
	- `password_hash` (TEXT NOT NULL) *(or plain for MVP only if explicitly requested)*
	- `created_at` (TEXT NOT NULL)

- `boards`
	- `id` (TEXT PK)
	- `user_id` (TEXT NOT NULL UNIQUE, FK -> users.id)
	- `name` (TEXT NOT NULL DEFAULT 'My Board')
	- `state_json` (TEXT NOT NULL)  // entire board JSON
	- `created_at` (TEXT NOT NULL)
	- `updated_at` (TEXT NOT NULL)

- `chat_messages` *(optional now, likely needed by Part 9)*
	- `id` (TEXT PK)
	- `user_id` (TEXT NOT NULL, FK -> users.id)
	- `role` (TEXT NOT NULL) // `user` | `assistant`
	- `content` (TEXT NOT NULL)
	- `created_at` (TEXT NOT NULL)

DB location:
- `backend/data/app.db`

### Checklist
- [x] Write schema doc in `docs/` (tables, constraints, migration/init approach).
- [x] Define board JSON shape and version field.
- [x] Define initialization flow when DB does not exist.

### Tests
- [x] DB file auto-created when missing.
- [x] Seed user/board creation works.
- [x] Read/write of `state_json` round-trip works with no data loss.

### Success criteria
- [x] Schema approved by user before API implementation.

### Approval checkpoint
- [x] User approves proposed schema and storage approach.

---

## Part 6: Backend API for board CRUD-like operations

### Objective
Expose authenticated API routes to fetch and modify board state.

### Checklist
- [x] Implement DB init on startup if missing.
- [x] Add API routes (tentative):
	- [x] `GET /api/board`
	- [x] `PUT /api/board`
	- [x] `POST /api/board/cards`
	- [x] `PATCH /api/board/cards/{cardId}`
	- [x] `DELETE /api/board/cards/{cardId}`
	- [x] `PATCH /api/board/columns/{columnId}`
- [x] Add input validation and minimal error handling.
- [x] Keep logic simple and predictable.

### Tests
- [x] Backend unit tests for service/repository methods.
- [x] API tests for auth-required behavior.
- [x] API tests for board updates and persistence.

### Success criteria
- [x] Board changes persist in SQLite and survive restart.

---

## Part 7: Frontend integration with backend

### Objective
Replace in-memory board state with backend-backed persisted state.

### Checklist
- [ ] Add frontend API client utilities.
- [ ] Load board from backend after login/session check.
- [ ] Persist edits (rename, move, add, delete) through API.
- [ ] Add lightweight loading/error UI states.

### Tests
- [ ] Unit tests for frontend data layer (if extracted).
- [ ] Integration tests for load + mutate flows.
- [ ] E2E: change board, refresh, verify persistence.

### Success criteria
- [ ] UI behavior remains smooth and data persists across reload.

### Approval checkpoint
- [ ] User validates persisted Kanban UX.

---

## Part 8: AI connectivity via OpenRouter

### Objective
Establish backend AI call capability and verify with deterministic smoke test.

### Checklist
- [ ] Add OpenRouter client configuration in backend.
- [ ] Read `OPENROUTER_API_KEY` from root `.env` (in container env).
- [ ] Set model to `openai/gpt-oss-120b`.
- [ ] Add internal service method or test route for connectivity check.

### Tests
- [ ] Execute backend test call with prompt `2+2`.
- [ ] Verify non-error response and expected numerical result.

### Success criteria
- [ ] AI call is reliable and logs are sufficient for troubleshooting.

---

## Part 9: Structured AI outputs for chat + board updates

### Objective
Send board JSON + user prompt + chat history to AI and receive typed structured output.

### Proposed structured output (for approval)

```json
{
	"assistant_message": "string",
	"operations": [
		{
			"type": "create_card | update_card | move_card | delete_card | rename_column",
			"card_id": "string (when needed)",
			"column_id": "string (when needed)",
			"target_column_id": "string (for move)",
			"title": "string (optional)",
			"details": "string (optional)",
			"position": "number (optional, zero-based)",
			"new_title": "string (for rename_column)"
		}
	]
}
```

Notes:
- `assistant_message` is always required.
- `operations` can be an empty array when no board change is needed.
- Backend validates and safely applies operations.

### Checklist
- [ ] Define strict response schema and validation.
- [ ] Build AI prompt contract (board JSON + conversation context).
- [ ] Apply validated operations transactionally.
- [ ] Persist assistant/user messages as needed.

### Tests
- [ ] Unit tests for operation validator.
- [ ] Unit tests for operation applier (all operation types).
- [ ] Integration tests for no-op and multi-op responses.
- [ ] Failure-path tests for malformed AI output.

### Success criteria
- [ ] AI responses are deterministic in shape and safe to apply.

### Approval checkpoint
- [ ] User approves structured output schema before UI chat integration.

---

## Part 10: Sidebar AI chat UX + live board refresh

### Objective
Add a clean sidebar chat experience that can update board state via structured AI operations.

### Checklist
- [ ] Add sidebar layout and chat panel components.
- [ ] Add message list, input, submit, and loading states.
- [ ] Wire chat submission to backend AI endpoint.
- [ ] Apply board updates from AI response and refresh UI automatically.
- [ ] Keep design aligned with project color scheme.

### Tests
- [ ] Frontend component tests for chat interactions.
- [ ] E2E test: ask AI to create/move/edit card and verify board updates.
- [ ] E2E test: AI response with no operations leaves board unchanged.

### Success criteria
- [ ] User can chat naturally and see board changes reflected immediately.

---

## Execution order and quality gates

- [ ] Complete each part in sequence.
- [ ] Run relevant tests before moving to next part.
- [ ] Stop at each approval checkpoint and wait for user sign-off.
- [ ] Keep implementation concise and root-cause-driven when issues appear.