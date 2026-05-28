from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from db import initialize_database
from main import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("PM_DB_PATH", str(db_path))
    initialize_database(db_path)
    return TestClient(app)


def _login(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )
    assert response.status_code == 200


def test_requires_auth_for_board(client: TestClient) -> None:
    response = client.get("/api/board")
    assert response.status_code == 401


def test_login_and_get_board(client: TestClient) -> None:
    _login(client)
    response = client.get("/api/board")
    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == 1
    assert len(payload["columns"]) == 5
    assert "card-1" in payload["cards"]


def test_put_board_round_trip(client: TestClient) -> None:
    _login(client)
    board_response = client.get("/api/board")
    board = board_response.json()

    board["columns"][0]["title"] = "Inbox"
    put_response = client.put("/api/board", json=board)
    assert put_response.status_code == 200

    refreshed = client.get("/api/board")
    assert refreshed.status_code == 200
    assert refreshed.json()["columns"][0]["title"] == "Inbox"


def test_create_update_move_and_delete_card(client: TestClient) -> None:
    _login(client)

    create_response = client.post(
        "/api/board/cards",
        json={
            "column_id": "col-backlog",
            "title": "API card",
            "details": "Created from test",
            "card_id": "card-api-test",
        },
    )
    assert create_response.status_code == 200
    assert "card-api-test" in create_response.json()["cards"]

    update_response = client.patch(
        "/api/board/cards/card-api-test",
        json={"title": "API card updated", "details": "Updated"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["cards"]["card-api-test"]["title"] == "API card updated"

    move_response = client.patch(
        "/api/board/cards/card-api-test",
        json={"target_column_id": "col-review", "position": 0},
    )
    assert move_response.status_code == 200
    review_col = next(
        col for col in move_response.json()["columns"] if col["id"] == "col-review"
    )
    assert review_col["cardIds"][0] == "card-api-test"

    delete_response = client.delete("/api/board/cards/card-api-test")
    assert delete_response.status_code == 200
    assert "card-api-test" not in delete_response.json()["cards"]


def test_rename_column(client: TestClient) -> None:
    _login(client)

    response = client.patch(
        "/api/board/columns/col-backlog",
        json={"title": "Ideas"},
    )
    assert response.status_code == 200

    backlog_col = next(col for col in response.json()["columns"] if col["id"] == "col-backlog")
    assert backlog_col["title"] == "Ideas"
