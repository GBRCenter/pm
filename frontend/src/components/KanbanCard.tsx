import { useEffect, useRef, useState } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import clsx from "clsx";
import type { Card } from "@/lib/kanban";

type KanbanCardProps = {
  card: Card;
  onDelete: (cardId: string) => void;
  onEdit: (cardId: string, changes: { title?: string; details?: string }) => void;
};

export const KanbanCard = ({ card, onDelete, onEdit }: KanbanCardProps) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: card.id });

  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [draftTitle, setDraftTitle] = useState(card.title);
  const [isEditingDetails, setIsEditingDetails] = useState(false);
  const [draftDetails, setDraftDetails] = useState(card.details);
  const titleInputRef = useRef<HTMLInputElement>(null);
  const detailsTextareaRef = useRef<HTMLTextAreaElement>(null);
  const skipTitleRef = useRef(false);
  const skipDetailsRef = useRef(false);

  useEffect(() => { setDraftTitle(card.title); }, [card.title]);
  useEffect(() => { setDraftDetails(card.details); }, [card.details]);

  useEffect(() => {
    if (isEditingTitle) titleInputRef.current?.focus();
  }, [isEditingTitle]);

  useEffect(() => {
    if (isEditingDetails) detailsTextareaRef.current?.focus();
  }, [isEditingDetails]);

  const commitTitle = () => {
    setIsEditingTitle(false);
    if (skipTitleRef.current) {
      skipTitleRef.current = false;
      setDraftTitle(card.title);
      return;
    }
    const title = draftTitle.trim();
    if (!title || title === card.title) {
      setDraftTitle(card.title);
      return;
    }
    onEdit(card.id, { title });
  };

  const commitDetails = () => {
    setIsEditingDetails(false);
    if (skipDetailsRef.current) {
      skipDetailsRef.current = false;
      setDraftDetails(card.details);
      return;
    }
    const details = draftDetails.trim();
    if (details === card.details) return;
    onEdit(card.id, { details });
  };

  return (
    <article
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={clsx(
        "rounded-2xl border border-transparent bg-white px-4 py-4 shadow-[0_12px_24px_rgba(3,33,71,0.08)]",
        "transition-all duration-150",
        isDragging && "opacity-60 shadow-[0_18px_32px_rgba(3,33,71,0.16)]"
      )}
      data-testid={`card-${card.id}`}
    >
      <div className="flex items-start gap-2">
        <div
          {...attributes}
          {...listeners}
          className="mt-1 shrink-0 cursor-grab touch-none text-[var(--gray-text)] active:cursor-grabbing"
          aria-label="Drag card"
        >
          <svg width="10" height="16" viewBox="0 0 10 16" fill="currentColor" aria-hidden="true">
            <circle cx="2" cy="4" r="1.5" />
            <circle cx="8" cy="4" r="1.5" />
            <circle cx="2" cy="8" r="1.5" />
            <circle cx="8" cy="8" r="1.5" />
            <circle cx="2" cy="12" r="1.5" />
            <circle cx="8" cy="12" r="1.5" />
          </svg>
        </div>
        <div className="min-w-0 flex-1">
          {isEditingTitle ? (
            <input
              ref={titleInputRef}
              value={draftTitle}
              onChange={(e) => setDraftTitle(e.target.value)}
              onBlur={commitTitle}
              onKeyDown={(e) => {
                if (e.key === "Enter") e.currentTarget.blur();
                if (e.key === "Escape") {
                  skipTitleRef.current = true;
                  e.currentTarget.blur();
                }
              }}
              className="w-full bg-transparent font-display text-base font-semibold text-[var(--navy-dark)] outline-none"
            />
          ) : (
            <h4
              onClick={() => setIsEditingTitle(true)}
              className="cursor-text font-display text-base font-semibold text-[var(--navy-dark)]"
            >
              {card.title}
            </h4>
          )}
          {isEditingDetails ? (
            <textarea
              ref={detailsTextareaRef}
              value={draftDetails}
              onChange={(e) => setDraftDetails(e.target.value)}
              onBlur={commitDetails}
              onKeyDown={(e) => {
                if (e.key === "Escape") {
                  skipDetailsRef.current = true;
                  e.currentTarget.blur();
                }
              }}
              rows={3}
              className="mt-1 w-full resize-none bg-transparent text-sm leading-6 text-[var(--gray-text)] outline-none"
            />
          ) : (
            <p
              onClick={() => setIsEditingDetails(true)}
              className="mt-2 cursor-text text-sm leading-6 text-[var(--gray-text)]"
            >
              {card.details}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={() => onDelete(card.id)}
          className="shrink-0 rounded-full border border-transparent px-2 py-1 text-xs font-semibold text-[var(--gray-text)] transition hover:border-[var(--stroke)] hover:text-[var(--navy-dark)]"
          aria-label={`Delete ${card.title}`}
        >
          Remove
        </button>
      </div>
    </article>
  );
};
