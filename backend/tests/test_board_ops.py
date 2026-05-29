from __future__ import annotations

from copy import deepcopy

import pytest

from ai import parse_board_response
from board_ops import BoardOperationError
from board_ops import apply_operations
from db import INITIAL_BOARD_STATE


def test_apply_operations_handles_all_supported_operation_types() -> None:
    board = deepcopy(INITIAL_BOARD_STATE)
    response = parse_board_response(
        """
        {
          "assistant_message": "Updated the board.",
          "operations": [
            {
              "type": "create_card",
              "column_id": "col-backlog",
              "card_id": "card-ai",
              "title": "AI card",
              "details": "Created by AI",
              "position": 1
            },
            {
              "type": "update_card",
              "card_id": "card-ai",
              "title": "AI card updated",
              "details": "Updated by AI"
            },
            {
              "type": "move_card",
              "card_id": "card-ai",
              "target_column_id": "col-review",
              "position": 0
            },
            {
              "type": "delete_card",
              "card_id": "card-6"
            },
            {
              "type": "rename_column",
              "column_id": "col-done",
              "new_title": "Complete"
            }
          ]
        }
        """
    )

    result = apply_operations(board, response.operations)

    assert result["cards"]["card-ai"] == {
        "id": "card-ai",
        "title": "AI card updated",
        "details": "Updated by AI",
    }
    review_column = next(column for column in result["columns"] if column["id"] == "col-review")
    done_column = next(column for column in result["columns"] if column["id"] == "col-done")
    assert review_column["cardIds"][0] == "card-ai"
    assert "card-6" not in result["cards"]
    assert done_column["title"] == "Complete"


def test_apply_operations_does_not_mutate_input_on_failure() -> None:
    board = deepcopy(INITIAL_BOARD_STATE)
    response = parse_board_response(
        """
        {
          "assistant_message": "Trying an invalid move.",
          "operations": [
            {
              "type": "move_card",
              "card_id": "card-1",
              "target_column_id": "missing-column"
            }
          ]
        }
        """
    )

    with pytest.raises(BoardOperationError):
        apply_operations(board, response.operations)

    assert board == INITIAL_BOARD_STATE
