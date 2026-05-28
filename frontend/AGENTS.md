# Frontend overview (current baseline)

This document describes the current state of the frontend in `frontend/`.

## Tech stack

- Next.js `16.1.6` (App Router)
- React `19.2.3`
- TypeScript
- Tailwind CSS `v4`
- DnD Kit (`@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities`)
- Testing:
  - Vitest + Testing Library (unit/component)
  - Playwright (e2e)

## Current app behavior

- Route `/` renders `KanbanBoard` from `src/components/KanbanBoard.tsx`.
- Login is required before board access.
- The board loads from the FastAPI backend via `/api/board`.
- Board changes persist to SQLite through backend API routes.
- Board has 5 fixed columns seeded by the backend for the demo user.
- Features currently implemented:
  - Rename columns
  - Add cards
  - Delete cards
  - Drag and drop cards within/between columns
- No AI chat UI yet.

## Key files

- `src/app/layout.tsx`
  - Root layout, metadata, and fonts.
- `src/app/page.tsx`
  - Home route rendering `KanbanBoard`.
- `src/app/globals.css`
  - Global styles and color tokens matching project palette.
- `src/components/KanbanBoard.tsx`
  - Main board container and state management.
- `src/components/KanbanColumn.tsx`
  - Column rendering, drop zone, title editing, new card form.
- `src/components/KanbanCard.tsx`
  - Sortable card component and delete action.
- `src/components/KanbanCardPreview.tsx`
  - Drag overlay card preview.
- `src/components/NewCardForm.tsx`
  - Inline form to add cards.
- `src/lib/api.ts`
  - Typed frontend client for auth and board API calls.
- `src/lib/kanban.ts`
  - Types, seeded test data, and card movement logic.

## Tests currently present

- Unit/component tests:
  - `src/components/KanbanBoard.test.tsx`
  - `src/lib/kanban.test.ts`
- E2E tests:
  - `tests/kanban.spec.ts`

## NPM scripts

- `npm run dev` - development server
- `npm run build` - production build
- `npm run start` - production server
- `npm run test:unit` - unit tests
- `npm run test:e2e` - Playwright tests
- `npm run test:all` - unit + e2e

## Notes for upcoming integration

- AI chat is not implemented yet.
- E2E tests run against FastAPI serving the static Next.js export.
