from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from ai import AiSmokeResult
from ai import OpenRouterConfigurationError
from ai import parse_board_response
from db import get_recent_chat_messages_for_username
from db import initialize_database
import main
from main import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_path = tmp_path / "app.db"
    monkeypatch.setattr(main, "DB_PATH", db_path)
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


def test_ai_smoke_test_requires_auth(client: TestClient) -> None:
    response = client.post("/api/ai/smoke-test")
    assert response.status_code == 401


def test_ai_smoke_test_returns_model_and_answer(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        main,
        "run_smoke_test",
        lambda: AiSmokeResult(model="openai/gpt-oss-120b", answer="4"),
    )
    _login(client)

    response = client.post("/api/ai/smoke-test")

    assert response.status_code == 200
    assert response.json() == {
        "model": "openai/gpt-oss-120b",
        "prompt": "2+2",
        "answer": "4",
        "ok": True,
    }


def test_ai_smoke_test_reports_missing_key(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_smoke_test() -> AiSmokeResult:
        raise OpenRouterConfigurationError("OPENROUTER_API_KEY is not configured")

    monkeypatch.setattr(main, "run_smoke_test", fail_smoke_test)
    _login(client)

    response = client.post("/api/ai/smoke-test")

    assert response.status_code == 503


def test_get_chat_history_requires_auth(client: TestClient) -> None:
    response = client.get("/api/ai/chat/history")
    assert response.status_code == 401


def test_get_chat_history_returns_messages_in_order(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        main,
        "run_board_chat",
        lambda *_args, **_kwargs: parse_board_response(
            '{"assistant_message": "History response.", "operations": []}'
        ),
    )
    _login(client)
    client.post("/api/ai/chat", json={"message": "History test message"})

    response = client.get("/api/ai/chat/history")
    assert response.status_code == 200
    messages = response.json()
    assert len(messages) == 2
    assert messages[0] == {"role": "user", "content": "History test message"}
    assert messages[1] == {"role": "assistant", "content": "History response."}


def test_ai_chat_requires_auth(client: TestClient) -> None:
    response = client.post("/api/ai/chat", json={"message": "Add a card"})
    assert response.status_code == 401


def test_ai_chat_persists_no_op_chat_messages(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        main,
        "run_board_chat",
        lambda *_args, **_kwargs: parse_board_response(
            '{"assistant_message": "No changes needed.", "operations": []}'
        ),
    )
    _login(client)

    response = client.post("/api/ai/chat", json={"message": "What is next?"})

    assert response.status_code == 200
    assert response.json()["assistant_message"] == "No changes needed."
    assert response.json()["operations"] == []

    messages = get_recent_chat_messages_for_username("user", db_path=main.DB_PATH)
    assert [(message.role, message.content) for message in messages] == [
        ("user", "What is next?"),
        ("assistant", "No changes needed."),
    ]


def test_ai_chat_applies_and_persists_multiple_operations(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        main,
        "run_board_chat",
        lambda *_args, **_kwargs: parse_board_response(
            """
            {
              "assistant_message": "Created a card and renamed the Done column.",
              "operations": [
                {
                  "type": "create_card",
                  "column_id": "col-backlog",
                  "card_id": "card-ai-api",
                  "title": "AI API card",
                  "details": "Created in integration test"
                },
                {
                  "type": "rename_column",
                  "column_id": "col-done",
                  "new_title": "Complete"
                }
              ]
            }
            """
        ),
    )
    _login(client)

    response = client.post("/api/ai/chat", json={"message": "Create a card"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["board"]["cards"]["card-ai-api"]["title"] == "AI API card"

    refreshed = client.get("/api/board")
    done_column = next(
        column for column in refreshed.json()["columns"] if column["id"] == "col-done"
    )
    assert refreshed.json()["cards"]["card-ai-api"]["details"] == "Created in integration test"
    assert done_column["title"] == "Complete"


def test_ai_chat_rejects_invalid_operations_without_persisting_messages(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        main,
        "run_board_chat",
        lambda *_args, **_kwargs: parse_board_response(
            """
            {
              "assistant_message": "Invalid operation.",
              "operations": [
                {
                  "type": "move_card",
                  "card_id": "card-1",
                  "target_column_id": "missing-column"
                }
              ]
            }
            """
        ),
    )
    _login(client)

    response = client.post("/api/ai/chat", json={"message": "Move a card"})

    assert response.status_code == 400
    messages = get_recent_chat_messages_for_username("user", db_path=main.DB_PATH)
    assert messages == []
