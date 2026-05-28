from pathlib import Path
import secrets

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="Project Management MVP API")

STATIC_DIR = Path(__file__).resolve().parent / "static"
INDEX_FILE = STATIC_DIR / "index.html"
SESSION_COOKIE_NAME = "pm_session"
VALID_USERNAME = "user"
VALID_PASSWORD = "password"
active_sessions: dict[str, str] = {}


class LoginRequest(BaseModel):
    username: str
    password: str


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
    if payload.username != VALID_USERNAME or payload.password != VALID_PASSWORD:
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
