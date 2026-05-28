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
- In-memory Kanban board only (no backend persistence yet).
- Board has 5 fixed columns seeded from `src/lib/kanban.ts`.
- Features currently implemented:
  - Rename columns
  - Add cards
  - Delete cards
  - Drag and drop cards within/between columns
- No authentication yet.
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
- `src/lib/kanban.ts`
  - Types, seeded data, card movement logic, ID utility.

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

- Frontend state is local and should later be replaced with API-backed persistence.
- Existing tests should be adapted incrementally as auth and backend integration are introduced.
