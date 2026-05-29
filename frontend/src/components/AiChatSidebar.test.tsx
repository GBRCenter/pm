import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AiChatSidebar } from "@/components/AiChatSidebar";
import { initialData, type BoardData } from "@/lib/kanban";

const originalFetch = global.fetch;

const cloneBoard = (board: BoardData = initialData): BoardData =>
  JSON.parse(JSON.stringify(board)) as BoardData;

const mockResponse = (payload: unknown, ok = true, status = ok ? 200 : 500) => ({
  ok,
  status,
  json: async () => payload,
});

describe("AiChatSidebar", () => {
  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("sends a message and applies the returned board", async () => {
    const updatedBoard = cloneBoard();
    updatedBoard.cards["card-ai-test"] = {
      id: "card-ai-test",
      title: "AI generated card",
      details: "Added by assistant.",
    };
    updatedBoard.columns[0].cardIds.push("card-ai-test");

    const fetchMock = vi.fn().mockResolvedValue(
      mockResponse({
        assistant_message: "I added the card.",
        operations: [
          {
            type: "create_card",
            card_id: "card-ai-test",
            column_id: "col-backlog",
            title: "AI generated card",
            details: "Added by assistant.",
          },
        ],
        board: updatedBoard,
      })
    );
    const onBoardUpdated = vi.fn();
    global.fetch = fetchMock as unknown as typeof fetch;

    render(<AiChatSidebar onBoardUpdated={onBoardUpdated} />);

    await userEvent.type(screen.getByLabelText("Message AI"), "Add a card");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      expect(screen.getByText("I added the card.")).toBeInTheDocument();
    });

    expect(onBoardUpdated).toHaveBeenCalledWith(updatedBoard);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/ai/chat",
      expect.objectContaining({
        body: JSON.stringify({ message: "Add a card" }),
        credentials: "include",
        method: "POST",
      })
    );
  });

  it("shows an error when the AI request fails", async () => {
    global.fetch = vi
      .fn()
      .mockResolvedValue(mockResponse({ detail: "Missing key" }, false, 503)) as unknown as typeof fetch;

    render(<AiChatSidebar onBoardUpdated={vi.fn()} />);

    await userEvent.type(screen.getByLabelText("Message AI"), "Summarize board");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "AI service is not configured."
      );
    });
  });
});
