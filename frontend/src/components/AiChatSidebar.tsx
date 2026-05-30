import { useEffect, useRef, useState, type FormEvent } from "react";
import { ApiError, getChatHistory, sendAiChatMessage } from "@/lib/api";
import type { BoardData } from "@/lib/kanban";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

type AiChatSidebarProps = {
  onBoardUpdated: (board: BoardData) => void;
};

const createMessageId = () =>
  `chat-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const getErrorMessage = (error: unknown) => {
  if (error instanceof ApiError && error.status === 503) {
    return "AI service is not configured.";
  }
  return "Could not get an AI response.";
};

export const AiChatSidebar = ({ onBoardUpdated }: AiChatSidebarProps) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draftMessage, setDraftMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    getChatHistory()
      .then((history) => {
        if (!cancelled) {
          setMessages(
            history.map((m) => ({ id: createMessageId(), role: m.role, content: m.content }))
          );
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const container = messagesContainerRef.current;
    if (container && messages.length > 0) {
      container.scrollTop = container.scrollHeight;
    }
  }, [messages]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const userMessage = draftMessage.trim();
    if (!userMessage || isSubmitting) {
      return;
    }

    setDraftMessage("");
    setErrorMessage(null);
    setIsSubmitting(true);
    setMessages((currentMessages) => [
      ...currentMessages,
      {
        id: createMessageId(),
        role: "user",
        content: userMessage,
      },
    ]);

    try {
      const response = await sendAiChatMessage(userMessage);
      onBoardUpdated(response.board);
      setMessages((currentMessages) => [
        ...currentMessages,
        {
          id: createMessageId(),
          role: "assistant",
          content: response.assistant_message,
        },
      ]);
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <aside
      className="flex h-full flex-col rounded-3xl border border-[var(--stroke)] bg-white p-4 shadow-[var(--shadow)]"
      aria-label="AI chat"
    >
      <div className="border-b border-[var(--stroke)] pb-4">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
          Assistant
        </p>
        <h2 className="mt-2 font-display text-xl font-semibold text-[var(--navy-dark)]">
          AI Chat
        </h2>
      </div>

      <div
        ref={messagesContainerRef}
        className="mt-4 flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto rounded-2xl bg-[var(--surface)] p-3"
        role="log"
        aria-label="AI chat messages"
        aria-live="polite"
      >
        {messages.length === 0 ? (
          <p className="m-auto text-center text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
            No messages yet
          </p>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={
                message.role === "user"
                  ? "ml-auto max-w-[88%] rounded-2xl bg-[var(--primary-blue)] px-4 py-3 text-sm font-medium leading-6 text-white"
                  : "mr-auto max-w-[88%] rounded-2xl border border-[var(--stroke)] bg-white px-4 py-3 text-sm leading-6 text-[var(--navy-dark)]"
              }
            >
              <p className="break-words">{message.content}</p>
            </div>
          ))
        )}

        {isSubmitting ? (
          <p
            className="mr-auto rounded-2xl border border-[var(--stroke)] bg-white px-4 py-3 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]"
            role="status"
          >
            Thinking...
          </p>
        ) : null}
      </div>

      {errorMessage ? (
        <p className="mt-3 text-sm font-medium text-[#b42318]" role="alert">
          {errorMessage}
        </p>
      ) : null}

      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3">
        <textarea
          value={draftMessage}
          onChange={(event) => setDraftMessage(event.target.value)}
          className="min-h-24 w-full resize-none rounded-2xl border border-[var(--stroke)] bg-white px-4 py-3 text-sm leading-6 text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
          aria-label="Message AI"
          placeholder="Message AI"
          disabled={isSubmitting}
        />
        <button
          type="submit"
          className="rounded-full bg-[var(--secondary-purple)] px-4 py-3 text-xs font-semibold uppercase tracking-wide text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isSubmitting || !draftMessage.trim()}
        >
          {isSubmitting ? "Sending..." : "Send"}
        </button>
      </form>
    </aside>
  );
};
