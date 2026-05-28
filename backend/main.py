from __future__ import annotations

from contextlib import asynccontextmanager
import os
from pathlib import Path
import secrets
from typing import Any

from db import get_board_for_username
from db import initialize_database
from db import save_board_for_username
from db import verify_credentials
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pydantic import Field


def _db_path() -> Path | None:
    raw = os.getenv("PM_DB_PATH")
    if not raw:
        return None
    return Path(raw)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database(_db_path())
    yield


app = FastAPI(title="Project Management MVP API", lifespan=lifespan)

STATIC_DIR = Path(__file__).resolve().parent / "static"
INDEX_FILE = STATIC_DIR / "index.html"
SESSION_COOKIE_NAME = "pm_session"
active_sessions: dict[str, str] = {}


class LoginRequest(BaseModel):
    username: str
    password: str


class CardCreateRequest(BaseModel):
    column_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    details: str = ""
    card_id: str | None = None
    position: int | None = Field(default=None, ge=0)


class CardUpdateRequest(BaseModel):
    title: str | None = None
    details: str | None = None
    target_column_id: str | None = None
    position: int | None = Field(default=None, ge=0)


class ColumnUpdateRequest(BaseModel):
    title: str = Field(min_length=1)


def _resolve_static_path(relative_path: str) -> Path:
    base = STATIC_DIR.resolve()
    candidate = (STATIC_DIR / relative_path).resolve()
    if not str(candidate).startswith(str(base)):
        raise HTTPException(status_code=404, detail="Not found")
    return candidate


def _get_authenticated_username(request: Request) -> str | None:
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_token:
        return None
    return active_sessions.get(session_token)


def _require_authenticated_username(request: Request) -> str:
    username = _get_authenticated_username(request)
    if not username:
        raise HTTPException(status_code=401, detail="Authentication required")
    return username


def _validate_board_state_shape(board_state: dict[str, Any]) -> bool:
    columns = board_state.get("columns")
    cards = board_state.get("cards")
    if not isinstance(columns, list) or not isinstance(cards, dict):
        return False

    if "version" not in board_state:
        board_state["version"] = 1

    seen_card_ids: set[str] = set()
    for column in columns:
        if not isinstance(column, dict):
            return False
        if not isinstance(column.get("id"), str) or not isinstance(column.get("title"), str):
            return False
        card_ids = column.get("cardIds")
        if not isinstance(card_ids, list):
            return False
        for card_id in card_ids:
            if not isinstance(card_id, str):
                return False
            if card_id not in cards:
                return False
            if card_id in seen_card_ids:
                return False
            seen_card_ids.add(card_id)

    for card_id, card in cards.items():
        if not isinstance(card_id, str) or not isinstance(card, dict):
            return False
        if not isinstance(card.get("id"), str):
            return False
        if card.get("id") != card_id:
            return False
        if not isinstance(card.get("title"), str):
            return False
        if not isinstance(card.get("details"), str):
            return False

    return True


def _find_column(board: dict[str, Any], column_id: str) -> dict[str, Any] | None:
    for column in board["columns"]:
        if column["id"] == column_id:
            return column
    return None


def _find_column_for_card(board: dict[str, Any], card_id: str) -> dict[str, Any] | None:
    for column in board["columns"]:
        if card_id in column["cardIds"]:
            return column
    return None


def _load_board(username: str) -> dict[str, Any]:
    board = get_board_for_username(username, _db_path())
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    if not _validate_board_state_shape(board):
        raise HTTPException(status_code=500, detail="Stored board state is invalid")
    return board


def _save_board(username: str, board: dict[str, Any]) -> None:
    if not _validate_board_state_shape(board):
        raise HTTPException(status_code=400, detail="Invalid board payload")
    saved = save_board_for_username(username, board, _db_path())
    if not saved:
        raise HTTPException(status_code=404, detail="Board not found")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/auth/session")
def auth_session(request: Request) -> dict[str, str | bool | None]:
    username = _get_authenticated_username(request)
    return {
        "authenticated": bool(username),
        "username": username,
    }


@app.post("/api/auth/login")
def auth_login(payload: LoginRequest) -> JSONResponse:
    if not verify_credentials(payload.username, payload.password, _db_path()):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    session_token = secrets.token_urlsafe(32)
    active_sessions[session_token] = payload.username

    response = JSONResponse(
        content={
            "authenticated": True,
            "username": payload.username,
        }
    )
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )
    return response


@app.post("/api/auth/logout")
def auth_logout(request: Request) -> JSONResponse:
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if session_token:
        active_sessions.pop(session_token, None)

    response = JSONResponse(content={"authenticated": False})
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return response


@app.get("/api/board")
def get_board(request: Request) -> dict[str, Any]:
    username = _require_authenticated_username(request)
    return _load_board(username)


@app.put("/api/board")
def put_board(request: Request, board_state: dict[str, Any]) -> dict[str, Any]:
    username = _require_authenticated_username(request)
    _save_board(username, board_state)
    return board_state


@app.post("/api/board/cards")
def post_card(request: Request, payload: CardCreateRequest) -> dict[str, Any]:
    username = _require_authenticated_username(request)
    board = _load_board(username)

    column = _find_column(board, payload.column_id)
    if not column:
        raise HTTPException(status_code=404, detail="Column not found")

    card_id = payload.card_id or f"card-{secrets.token_hex(6)}"
    if card_id in board["cards"]:
        raise HTTPException(status_code=409, detail="Card id already exists")

    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Card title is required")
    details = payload.details.strip() or "No details yet."

    board["cards"][card_id] = {
        "id": card_id,
        "title": title,
        "details": details,
    }

    insert_position = payload.position
    if insert_position is None or insert_position > len(column["cardIds"]):
        column["cardIds"].append(card_id)
    else:
        column["cardIds"].insert(insert_position, card_id)

    _save_board(username, board)
    return board


@app.patch("/api/board/cards/{card_id}")
def patch_card(
    card_id: str,
    request: Request,
    payload: CardUpdateRequest,
) -> dict[str, Any]:
    username = _require_authenticated_username(request)
    board = _load_board(username)

    card = board["cards"].get(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    changed = False

    if payload.title is not None:
        title = payload.title.strip()
        if not title:
            raise HTTPException(status_code=400, detail="Card title cannot be empty")
        card["title"] = title
        changed = True

    if payload.details is not None:
        card["details"] = payload.details.strip()
        changed = True

    if payload.target_column_id is not None:
        source_column = _find_column_for_card(board, card_id)
        target_column = _find_column(board, payload.target_column_id)

        if not source_column:
            raise HTTPException(status_code=404, detail="Source column not found")
        if not target_column:
            raise HTTPException(status_code=404, detail="Target column not found")

        source_column["cardIds"] = [
            existing_card_id
            for existing_card_id in source_column["cardIds"]
            if existing_card_id != card_id
        ]

        insert_position = payload.position
        if insert_position is None or insert_position > len(target_column["cardIds"]):
            target_column["cardIds"].append(card_id)
        else:
            target_column["cardIds"].insert(insert_position, card_id)
        changed = True

    if not changed:
        raise HTTPException(status_code=400, detail="No updates provided")

    _save_board(username, board)
    return board


@app.delete("/api/board/cards/{card_id}")
def delete_card(card_id: str, request: Request) -> dict[str, Any]:
    username = _require_authenticated_username(request)
    board = _load_board(username)

    if card_id not in board["cards"]:
        raise HTTPException(status_code=404, detail="Card not found")

    del board["cards"][card_id]
    for column in board["columns"]:
        column["cardIds"] = [
            existing_card_id
            for existing_card_id in column["cardIds"]
            if existing_card_id != card_id
        ]

    _save_board(username, board)
    return board


@app.patch("/api/board/columns/{column_id}")
def patch_column(
    column_id: str,
    request: Request,
    payload: ColumnUpdateRequest,
) -> dict[str, Any]:
    username = _require_authenticated_username(request)
    board = _load_board(username)

    column = _find_column(board, column_id)
    if not column:
        raise HTTPException(status_code=404, detail="Column not found")

    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Column title cannot be empty")

    column["title"] = title
    _save_board(username, board)
    return board


@app.get("/")
def home() -> FileResponse:
    if INDEX_FILE.exists():
        return FileResponse(INDEX_FILE)
    raise HTTPException(
        status_code=503,
        detail="Frontend static build not found. Expected backend/static/index.html",
    )


@app.get("/{full_path:path}", include_in_schema=False)
def static_files(full_path: str) -> FileResponse:
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")

    requested = _resolve_static_path(full_path)
    if requested.is_file():
        return FileResponse(requested)

    if INDEX_FILE.exists():
        return FileResponse(INDEX_FILE)

    raise HTTPException(
        status_code=503,
        detail="Frontend static build not found. Expected backend/static/index.html",
    )
