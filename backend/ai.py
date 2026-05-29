from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
from typing import Annotated
from typing import Any
from typing import Literal

import httpx
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import ValidationError
from pydantic import model_validator

OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openai/gpt-oss-120b"
OPENROUTER_SMOKE_MAX_COMPLETION_TOKENS = 128
OPENROUTER_BOARD_MAX_COMPLETION_TOKENS = 1400
logger = logging.getLogger(__name__)


class OpenRouterConfigurationError(RuntimeError):
    pass


class OpenRouterResponseError(RuntimeError):
    pass


class AiResponseValidationError(RuntimeError):
    pass


@dataclass(frozen=True)
class AiSmokeResult:
    model: str
    answer: str


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class CreateCardOperation(_StrictModel):
    type: Literal["create_card"]
    column_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    details: str = ""
    card_id: str | None = Field(default=None, min_length=1)
    position: int | None = Field(default=None, ge=0)


class UpdateCardOperation(_StrictModel):
    type: Literal["update_card"]
    card_id: str = Field(min_length=1)
    title: str | None = Field(default=None, min_length=1)
    details: str | None = None

    @model_validator(mode="after")
    def require_card_change(self) -> "UpdateCardOperation":
        if self.title is None and self.details is None:
            raise ValueError("update_card requires title or details")
        return self


class MoveCardOperation(_StrictModel):
    type: Literal["move_card"]
    card_id: str = Field(min_length=1)
    target_column_id: str = Field(min_length=1)
    position: int | None = Field(default=None, ge=0)


class DeleteCardOperation(_StrictModel):
    type: Literal["delete_card"]
    card_id: str = Field(min_length=1)


class RenameColumnOperation(_StrictModel):
    type: Literal["rename_column"]
    column_id: str = Field(min_length=1)
    new_title: str = Field(min_length=1)


AiOperation = Annotated[
    CreateCardOperation
    | UpdateCardOperation
    | MoveCardOperation
    | DeleteCardOperation
    | RenameColumnOperation,
    Field(discriminator="type"),
]


class AiBoardResponse(_StrictModel):
    assistant_message: str = Field(min_length=1)
    operations: list[AiOperation] = Field(default_factory=list)


def _api_key() -> str:
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise OpenRouterConfigurationError("OPENROUTER_API_KEY is not configured")
    return key


def _response_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise OpenRouterResponseError("OpenRouter response did not include choices")

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise OpenRouterResponseError("OpenRouter response choice is invalid")

    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise OpenRouterResponseError("OpenRouter response did not include a message")

    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise OpenRouterResponseError("OpenRouter response content is empty")

    return content.strip()


def _chat_completion(
    messages: list[dict[str, str]],
    max_completion_tokens: int,
) -> str:
    try:
        response = httpx.post(
            OPENROUTER_CHAT_COMPLETIONS_URL,
            headers={
                "Authorization": f"Bearer {_api_key()}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": messages,
                "temperature": 0,
                "max_completion_tokens": max_completion_tokens,
            },
            timeout=30,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        logger.warning("OpenRouter request failed with status %s", status_code)
        raise OpenRouterResponseError(
            f"OpenRouter request failed with status {status_code}"
        ) from exc
    except httpx.HTTPError as exc:
        logger.warning("OpenRouter request failed: %s", exc.__class__.__name__)
        raise OpenRouterResponseError("OpenRouter request failed") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        logger.warning("OpenRouter returned non-JSON response")
        raise OpenRouterResponseError("OpenRouter response payload is invalid") from exc

    if not isinstance(payload, dict):
        raise OpenRouterResponseError("OpenRouter response payload is invalid")

    return _response_text(payload)


def call_openrouter(prompt: str) -> str:
    return _chat_completion(
        [
            {
                "role": "system",
                "content": "Reply with only the final answer. No explanation.",
            },
            {"role": "user", "content": prompt},
        ],
        OPENROUTER_SMOKE_MAX_COMPLETION_TOKENS,
    )


def run_smoke_test() -> AiSmokeResult:
    return AiSmokeResult(
        model=OPENROUTER_MODEL,
        answer=call_openrouter("2+2"),
    )


def parse_board_response(raw_text: str) -> AiBoardResponse:
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise AiResponseValidationError("AI response was not valid JSON") from exc

    try:
        return AiBoardResponse.model_validate(payload)
    except ValidationError as exc:
        raise AiResponseValidationError("AI response did not match schema") from exc


def _board_prompt(
    user_message: str,
    board: dict[str, Any],
    chat_history: list[dict[str, str]],
) -> str:
    return json.dumps(
        {
            "task": "Update a project management Kanban board from the user request.",
            "rules": [
                "Return only JSON. Do not use markdown.",
                "assistant_message is required.",
                "operations may be empty.",
                "Only use operation types: create_card, update_card, move_card, delete_card, rename_column.",
                "Use existing column and card ids from current_board when referencing existing items.",
                "If the request is unclear or impossible, explain briefly and return no operations.",
            ],
            "response_schema": {
                "assistant_message": "string",
                "operations": [
                    {
                        "type": "create_card | update_card | move_card | delete_card | rename_column",
                        "card_id": "string when needed",
                        "column_id": "string when needed",
                        "target_column_id": "string for move_card",
                        "title": "string when needed",
                        "details": "string optional",
                        "position": "integer optional, zero-based",
                        "new_title": "string for rename_column",
                    }
                ],
            },
            "current_board": board,
            "recent_chat_messages": chat_history,
            "user_message": user_message,
        },
        ensure_ascii=False,
    )


def run_board_chat(
    user_message: str,
    board: dict[str, Any],
    chat_history: list[dict[str, str]],
) -> AiBoardResponse:
    raw_text = _chat_completion(
        [
            {
                "role": "system",
                "content": (
                    "You are a project management assistant that edits a Kanban board. "
                    "Return only a JSON object that matches the requested schema."
                ),
            },
            {"role": "user", "content": _board_prompt(user_message, board, chat_history)},
        ],
        OPENROUTER_BOARD_MAX_COMPLETION_TOKENS,
    )
    return parse_board_response(raw_text)
