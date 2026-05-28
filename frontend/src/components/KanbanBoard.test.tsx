import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanBoard } from "@/components/KanbanBoard";
import { initialData, type BoardData } from "@/lib/kanban";

const getFirstColumn = () => screen.getAllByTestId(/column-/i)[0];
const originalFetch = global.fetch;

const cloneBoard = (board: BoardData = initialData): BoardData =>
  JSON.parse(JSON.stringify(board)) as BoardData;

const mockResponse = (payload: unknown, ok = true, status = ok ? 200 : 500) => ({
  ok,
  status,
  json: async () => payload,
});

describe("KanbanBoard", () => {
  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("renders five columns after loading the board", async () => {
    global.fetch = vi.fn().mockResolvedValue(mockResponse(cloneBoard())) as unknown as typeof fetch;

    render(<KanbanBoard />);

    await waitFor(() => {
      expect(screen.getAllByTestId(/column-/i)).toHaveLength(5);
    });
  });

  it("renames a column", async () => {
    const updatedBoard = cloneBoard();
    updatedBoard.columns[0].title = "New Name";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(mockResponse(cloneBoard()))
      .mockResolvedValueOnce(mockResponse(updatedBoard));
    global.fetch = fetchMock as unknown as typeof fetch;

    render(<KanbanBoard />);

    await waitFor(() => {
      expect(screen.getAllByTestId(/column-/i)).toHaveLength(5);
    });

    const column = getFirstColumn();
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    fireEvent.blur(input);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/board/columns/col-backlog",
        expect.objectContaining({ method: "PATCH" })
      );
    });

    expect(input).toHaveValue("New Name");
  });

  it("adds and removes a card", async () => {
    const addedBoard = cloneBoard();
    addedBoard.cards["card-api-test"] = {
      id: "card-api-test",
      title: "New card",
      details: "Notes",
    };
    addedBoard.columns[0].cardIds.push("card-api-test");

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(mockResponse(cloneBoard()))
      .mockResolvedValueOnce(mockResponse(addedBoard))
      .mockResolvedValueOnce(mockResponse(cloneBoard()));
    global.fetch = fetchMock as unknown as typeof fetch;

    render(<KanbanBoard />);

    await waitFor(() => {
      expect(screen.getAllByTestId(/column-/i)).toHaveLength(5);
    });

    const column = getFirstColumn();
    const addButton = within(column).getByRole("button", {
      name: /add a card/i,
    });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    await waitFor(() => {
      expect(within(column).getByText("New card")).toBeInTheDocument();
    });

    const deleteButton = within(column).getByRole("button", {
      name: /delete new card/i,
    });
    await userEvent.click(deleteButton);

    await waitFor(() => {
      expect(within(column).queryByText("New card")).not.toBeInTheDocument();
    });
  });
});
