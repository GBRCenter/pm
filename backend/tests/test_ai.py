from __future__ import annotations

import json

import httpx
import pytest

from ai import OPENROUTER_CHAT_COMPLETIONS_URL
from ai import OPENROUTER_BOARD_MAX_COMPLETION_TOKENS
from ai import OPENROUTER_MODEL
from ai import OPENROUTER_SMOKE_MAX_COMPLETION_TOKENS
from ai import AiResponseValidationError
from ai import OpenRouterConfigurationError
from ai import OpenRouterResponseError
from ai import call_openrouter
from ai import parse_board_response
from ai import run_board_chat
from db import INITIAL_BOARD_STATE


class FakeResponse:
    status_code = 200

    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


def test_call_openrouter_posts_chat_completion_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    def fake_post(url: str, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "4",
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr("ai.httpx.post", fake_post)

    answer = call_openrouter("2+2")

    assert answer == "4"
    assert captured["url"] == OPENROUTER_CHAT_COMPLETIONS_URL
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == OPENROUTER_MODEL
    assert (
        captured["json"]["max_completion_tokens"]
        == OPENROUTER_SMOKE_MAX_COMPLETION_TOKENS
    )
    assert captured["json"]["messages"][-1] == {"role": "user", "content": "2+2"}


def test_call_openrouter_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(OpenRouterConfigurationError):
        call_openrouter("2+2")


def test_call_openrouter_rejects_invalid_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr("ai.httpx.post", lambda *_args, **_kwargs: FakeResponse({"choices": []}))

    with pytest.raises(OpenRouterResponseError):
        call_openrouter("2+2")


def test_call_openrouter_wraps_http_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    def fake_post(*_args, **_kwargs):
        request = httpx.Request("POST", OPENROUTER_CHAT_COMPLETIONS_URL)
        response = httpx.Response(401, request=request)
        raise httpx.HTTPStatusError("Unauthorized", request=request, response=response)

    monkeypatch.setattr("ai.httpx.post", fake_post)

    with pytest.raises(OpenRouterResponseError):
        call_openrouter("2+2")


def test_parse_board_response_rejects_malformed_json() -> None:
    with pytest.raises(AiResponseValidationError):
        parse_board_response("not json")


def test_parse_board_response_rejects_unknown_operation_fields() -> None:
    with pytest.raises(AiResponseValidationError):
        parse_board_response(
            """
            {
              "assistant_message": "Bad operation.",
              "operations": [
                {
                  "type": "delete_card",
                  "card_id": "card-1",
                  "unexpected": true
                }
              ]
            }
            """
        )


def test_run_board_chat_sends_board_history_and_user_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    def fake_post(url: str, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(
                                {
                                    "assistant_message": "No changes needed.",
                                    "operations": [],
                                }
                            ),
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr("ai.httpx.post", fake_post)

    response = run_board_chat(
        "What is on the board?",
        INITIAL_BOARD_STATE,
        [{"role": "user", "content": "Earlier message"}],
    )

    user_payload = json.loads(captured["json"]["messages"][1]["content"])
    assert response.assistant_message == "No changes needed."
    assert captured["json"]["max_completion_tokens"] == OPENROUTER_BOARD_MAX_COMPLETION_TOKENS
    assert user_payload["current_board"]["version"] == 1
    assert user_payload["recent_chat_messages"] == [
        {"role": "user", "content": "Earlier message"}
    ]
    assert user_payload["user_message"] == "What is on the board?"
