from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import uuid4

from ai import AiOperation
from ai import CreateCardOperation
from ai import DeleteCardOperation
from ai import MoveCardOperation
from ai import RenameColumnOperation
from ai import UpdateCardOperation


class BoardOperationError(ValueError):
    pass


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


def _insert_card_id(column: dict[str, Any], card_id: str, position: int | None) -> None:
    if position is None or position > len(column["cardIds"]):
        column["cardIds"].append(card_id)
    else:
        column["cardIds"].insert(position, card_id)


def _create_card(board: dict[str, Any], operation: CreateCardOperation) -> None:
    column = _find_column(board, operation.column_id)
    if not column:
        raise BoardOperationError("Column not found")

    title = operation.title.strip()
    if not title:
        raise BoardOperationError("Card title is required")

    card_id = operation.card_id or f"card-{uuid4().hex[:12]}"
    if card_id in board["cards"]:
        raise BoardOperationError("Card id already exists")

    board["cards"][card_id] = {
        "id": card_id,
        "title": title,
        "details": operation.details.strip() or "No details yet.",
    }
    _insert_card_id(column, card_id, operation.position)


def _update_card(board: dict[str, Any], operation: UpdateCardOperation) -> None:
    card = board["cards"].get(operation.card_id)
    if not card:
        raise BoardOperationError("Card not found")

    if operation.title is not None:
        title = operation.title.strip()
        if not title:
            raise BoardOperationError("Card title is required")
        card["title"] = title
    if operation.details is not None:
        card["details"] = operation.details.strip()


def _move_card(board: dict[str, Any], operation: MoveCardOperation) -> None:
    card = board["cards"].get(operation.card_id)
    if not card:
        raise BoardOperationError("Card not found")

    source_column = _find_column_for_card(board, operation.card_id)
    target_column = _find_column(board, operation.target_column_id)
    if not source_column:
        raise BoardOperationError("Source column not found")
    if not target_column:
        raise BoardOperationError("Target column not found")

    source_column["cardIds"] = [
        card_id for card_id in source_column["cardIds"] if card_id != operation.card_id
    ]
    _insert_card_id(target_column, operation.card_id, operation.position)


def _delete_card(board: dict[str, Any], operation: DeleteCardOperation) -> None:
    if operation.card_id not in board["cards"]:
        raise BoardOperationError("Card not found")

    del board["cards"][operation.card_id]
    for column in board["columns"]:
        column["cardIds"] = [
            card_id for card_id in column["cardIds"] if card_id != operation.card_id
        ]


def _rename_column(board: dict[str, Any], operation: RenameColumnOperation) -> None:
    column = _find_column(board, operation.column_id)
    if not column:
        raise BoardOperationError("Column not found")

    title = operation.new_title.strip()
    if not title:
        raise BoardOperationError("Column title is required")

    column["title"] = title


def apply_operations(
    board: dict[str, Any],
    operations: list[AiOperation],
) -> dict[str, Any]:
    next_board = deepcopy(board)

    for operation in operations:
        if isinstance(operation, CreateCardOperation):
            _create_card(next_board, operation)
        elif isinstance(operation, UpdateCardOperation):
            _update_card(next_board, operation)
        elif isinstance(operation, MoveCardOperation):
            _move_card(next_board, operation)
        elif isinstance(operation, DeleteCardOperation):
            _delete_card(next_board, operation)
        elif isinstance(operation, RenameColumnOperation):
            _rename_column(next_board, operation)
        else:
            raise BoardOperationError("Unsupported operation")

    return next_board
