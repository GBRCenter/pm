import {
  ApiError,
  createCard,
  fetchBoard,
  getSession,
  renameColumn,
} from "@/lib/api";
import { initialData } from "@/lib/kanban";

const originalFetch = global.fetch;

const mockResponse = (payload: unknown, ok = true, status = ok ? 200 : 500) => ({
  ok,
  status,
  json: async () => payload,
});

describe("api client", () => {
  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("fetches the active session with credentials", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      mockResponse({
        authenticated: true,
        username: "user",
      })
    );
    global.fetch = fetchMock as unknown as typeof fetch;

    const session = await getSession();

    expect(session).toEqual({ authenticated: true, username: "user" });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/session",
      expect.objectContaining({
        credentials: "include",
        method: "GET",
      })
    );
  });

  it("fetches the board", async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockResponse(initialData));
    global.fetch = fetchMock as unknown as typeof fetch;

    const board = await fetchBoard();

    expect(board.columns).toHaveLength(5);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/board",
      expect.objectContaining({
        credentials: "include",
        method: "GET",
      })
    );
  });

  it("maps card creation to the backend payload shape", async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockResponse(initialData));
    global.fetch = fetchMock as unknown as typeof fetch;

    await createCard({
      columnId: "col-backlog",
      title: "New card",
      details: "Notes",
      position: 1,
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/board/cards",
      expect.objectContaining({
        body: JSON.stringify({
          column_id: "col-backlog",
          title: "New card",
          details: "Notes",
          position: 1,
        }),
        credentials: "include",
        method: "POST",
      })
    );
  });

  it("renames columns through the backend", async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockResponse(initialData));
    global.fetch = fetchMock as unknown as typeof fetch;

    await renameColumn("col-backlog", "Ideas");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/board/columns/col-backlog",
      expect.objectContaining({
        body: JSON.stringify({ title: "Ideas" }),
        credentials: "include",
        method: "PATCH",
      })
    );
  });

  it("throws an ApiError with backend details", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(mockResponse({ detail: "Authentication required" }, false, 401));
    global.fetch = fetchMock as unknown as typeof fetch;

    await expect(fetchBoard()).rejects.toEqual(
      new ApiError("Authentication required", 401)
    );
  });
});
