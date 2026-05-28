import type { BoardData } from "@/lib/kanban";

export type SessionResponse = {
  authenticated: boolean;
  username: string | null;
};

type JsonRequestInit = Omit<RequestInit, "body"> & {
  body?: unknown;
};

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const requestJson = async <T>(
  path: string,
  options: JsonRequestInit = {}
): Promise<T> => {
  const { body, headers, ...init } = options;
  const requestHeaders = new Headers(headers);

  const response = await fetch(path, {
    ...init,
    credentials: "include",
    headers: requestHeaders,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const detail =
      payload &&
      typeof payload === "object" &&
      "detail" in payload &&
      typeof payload.detail === "string"
        ? payload.detail
        : `Request failed with status ${response.status}`;
    throw new ApiError(detail, response.status);
  }

  return payload as T;
};

const jsonHeaders = {
  "Content-Type": "application/json",
};

export const getSession = () =>
  requestJson<SessionResponse>("/api/auth/session", {
    method: "GET",
  });

export const login = (username: string, password: string) =>
  requestJson<SessionResponse>("/api/auth/login", {
    method: "POST",
    headers: jsonHeaders,
    body: { username, password },
  });

export const logout = () =>
  requestJson<{ authenticated: false }>("/api/auth/logout", {
    method: "POST",
  });

export const fetchBoard = () =>
  requestJson<BoardData>("/api/board", {
    method: "GET",
  });

export const saveBoard = (board: BoardData) =>
  requestJson<BoardData>("/api/board", {
    method: "PUT",
    headers: jsonHeaders,
    body: board,
  });

export const createCard = ({
  columnId,
  title,
  details,
  position,
}: {
  columnId: string;
  title: string;
  details: string;
  position?: number;
}) =>
  requestJson<BoardData>("/api/board/cards", {
    method: "POST",
    headers: jsonHeaders,
    body: {
      column_id: columnId,
      title,
      details,
      position,
    },
  });

export const updateCard = (
  cardId: string,
  payload: {
    title?: string;
    details?: string;
    targetColumnId?: string;
    position?: number;
  }
) =>
  requestJson<BoardData>(`/api/board/cards/${cardId}`, {
    method: "PATCH",
    headers: jsonHeaders,
    body: {
      title: payload.title,
      details: payload.details,
      target_column_id: payload.targetColumnId,
      position: payload.position,
    },
  });

export const deleteCard = (cardId: string) =>
  requestJson<BoardData>(`/api/board/cards/${cardId}`, {
    method: "DELETE",
  });

export const renameColumn = (columnId: string, title: string) =>
  requestJson<BoardData>(`/api/board/columns/${columnId}`, {
    method: "PATCH",
    headers: jsonHeaders,
    body: { title },
  });
