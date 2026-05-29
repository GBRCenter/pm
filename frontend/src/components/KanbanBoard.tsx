"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  pointerWithin,
  useSensor,
  useSensors,
  closestCorners,
  type CollisionDetection,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import {
  createCard as createCardRequest,
  deleteCard as deleteCardRequest,
  fetchBoard,
  renameColumn as renameColumnRequest,
  updateCard,
} from "@/lib/api";
import { moveCard, type BoardData, type Column } from "@/lib/kanban";

const getCardPlacement = (columns: Column[], cardId: string) => {
  const column = columns.find((candidate) => candidate.cardIds.includes(cardId));
  if (!column) {
    return null;
  }

  return {
    columnId: column.id,
    position: column.cardIds.indexOf(cardId),
  };
};

const removeCardFromBoard = (board: BoardData, cardId: string): BoardData => ({
  ...board,
  cards: Object.fromEntries(
    Object.entries(board.cards).filter(([id]) => id !== cardId)
  ),
  columns: board.columns.map((column) => ({
    ...column,
    cardIds: column.cardIds.filter((id) => id !== cardId),
  })),
});

export const KanbanBoard = () => {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  const cardsById = useMemo(() => board?.cards ?? {}, [board?.cards]);

  const collisionDetection = useCallback<CollisionDetection>(
    (args) => {
      const pointerCollisions = pointerWithin(args);
      const emptyColumnCollision = pointerCollisions.find((collision) =>
        board?.columns.some(
          (column) => column.id === collision.id && column.cardIds.length === 0
        )
      );

      if (emptyColumnCollision) {
        return [emptyColumnCollision];
      }

      return closestCorners(args);
    },
    [board?.columns]
  );

  const loadBoard = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      setBoard(await fetchBoard());
    } catch {
      setBoard(null);
      setErrorMessage("Could not load the board.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadBoard();
  }, [loadBoard]);

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);

    if (!board || !over || active.id === over.id) {
      return;
    }

    const cardId = active.id as string;
    const nextColumns = moveCard(board.columns, cardId, over.id as string);
    if (nextColumns === board.columns) {
      return;
    }

    const placement = getCardPlacement(nextColumns, cardId);
    if (!placement) {
      return;
    }

    const previousBoard = board;
    setBoard({ ...board, columns: nextColumns });
    setIsSaving(true);
    setErrorMessage(null);

    void updateCard(cardId, {
      targetColumnId: placement.columnId,
      position: placement.position,
    })
      .then(setBoard)
      .catch(() => {
        setBoard(previousBoard);
        setErrorMessage("Could not move the card.");
      })
      .finally(() => setIsSaving(false));
  };

  const handleRenameColumn = async (columnId: string, title: string) => {
    if (!board) {
      return;
    }

    const cleanTitle = title.trim();
    const previousBoard = board;
    const nextBoard = {
      ...board,
      columns: board.columns.map((column) =>
        column.id === columnId ? { ...column, title: cleanTitle } : column
      ),
    };

    setBoard(nextBoard);
    setIsSaving(true);
    setErrorMessage(null);

    try {
      setBoard(await renameColumnRequest(columnId, cleanTitle));
    } catch (error) {
      setBoard(previousBoard);
      setErrorMessage("Could not rename the column.");
      throw error;
    } finally {
      setIsSaving(false);
    }
  };

  const handleAddCard = async (
    columnId: string,
    title: string,
    details: string
  ) => {
    setIsSaving(true);
    setErrorMessage(null);

    try {
      setBoard(await createCardRequest({ columnId, title, details }));
    } catch (error) {
      setErrorMessage("Could not add the card.");
      throw error;
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteCard = (_columnId: string, cardId: string) => {
    if (!board) {
      return;
    }

    const previousBoard = board;
    setBoard(removeCardFromBoard(board, cardId));
    setIsSaving(true);
    setErrorMessage(null);

    void deleteCardRequest(cardId)
      .then(setBoard)
      .catch(() => {
        setBoard(previousBoard);
        setErrorMessage("Could not delete the card.");
      })
      .finally(() => setIsSaving(false));
  };

  const activeCard = activeCardId ? cardsById[activeCardId] : null;

  if (isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[var(--surface)] px-6 py-12">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
          Loading board...
        </p>
      </main>
    );
  }

  if (!board) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[var(--surface)] px-6 py-12">
        <section className="w-full max-w-md rounded-[24px] border border-[var(--stroke)] bg-white p-6 text-center shadow-[var(--shadow)]">
          <p className="text-sm font-semibold text-[#b42318]" role="alert">
            {errorMessage ?? "Board unavailable."}
          </p>
          <button
            type="button"
            onClick={() => void loadBoard()}
            className="mt-4 rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white transition hover:brightness-110"
          >
            Retry
          </button>
        </section>
      </main>
    );
  }

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1500px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Single Board Kanban
              </p>
              <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
                Keep momentum visible. Rename columns, drag cards between stages,
                and capture quick notes without getting buried in settings.
              </p>
            </div>
            <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                Focus
              </p>
              <p className="mt-2 text-lg font-semibold text-[var(--primary-blue)]">
                One board. Five columns. Zero clutter.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            {board.columns.map((column) => (
              <div
                key={column.id}
                className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]"
              >
                <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                {column.title}
              </div>
            ))}
          </div>
          <div className="min-h-5">
            {isSaving ? (
              <p
                className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]"
                role="status"
              >
                Saving...
              </p>
            ) : null}
            {errorMessage ? (
              <p className="text-sm font-medium text-[#b42318]" role="alert">
                {errorMessage}
              </p>
            ) : null}
          </div>
        </header>

        <DndContext
          sensors={sensors}
          collisionDetection={collisionDetection}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <section className="grid gap-6 lg:grid-cols-5">
            {board.columns.map((column) => (
              <KanbanColumn
                key={column.id}
                column={column}
                cards={column.cardIds.map((cardId) => board.cards[cardId])}
                onRename={handleRenameColumn}
                onAddCard={handleAddCard}
                onDeleteCard={handleDeleteCard}
              />
            ))}
          </section>
          <DragOverlay>
            {activeCard ? (
              <div className="w-[260px]">
                <KanbanCardPreview card={activeCard} />
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      </main>
    </div>
  );
};
