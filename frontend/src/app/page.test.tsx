import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Home from "@/app/page";

const originalFetch = global.fetch;

describe("Home auth flow", () => {
  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("shows login first and then board after successful login", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ authenticated: false, username: null }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ authenticated: true, username: "user" }),
      });

    global.fetch = fetchMock as unknown as typeof fetch;

    render(<Home />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Kanban Studio" })).toBeInTheDocument();
    });
  });

  it("shows invalid credentials message", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ authenticated: false, username: null }),
      })
      .mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: "Invalid credentials" }),
      });

    global.fetch = fetchMock as unknown as typeof fetch;

    render(<Home />);

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByText("Invalid credentials. Use user / password.")).toBeInTheDocument();
    });
  });
});