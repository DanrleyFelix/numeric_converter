from __future__ import annotations

from src.core.command_window.context import cmd_window_context
from src.core.command_window.tokenizer import Token, TokenType
from src.core.command_window.validator.errors import InvalidOperatorSequenceError, UnknownVariableError
from src.core.command_window.validator.validation_state import ValidationState
from src.core.constants import ERROR_INVALID_EXPRESSION


class SemanticValidator:
    def __init__(self, tokens: list[Token]):
        self._tokens = tokens

    def validate(self) -> ValidationState:
        self._check_variables()
        self._check_assignments()
        return ValidationState.ACCEPTABLE

    def _check_variables(self) -> None:
        for index, token in enumerate(self._tokens):
            if token.type != TokenType.IDENTIFIER:
                continue
            if self._is_left_hand_assignment(index):
                continue
            if cmd_window_context.get_variable(token.raw) is None:
                raise UnknownVariableError(
                    f'Unknown variable "{token.raw}".',
                    position=token.position,
                )

    def _is_left_hand_assignment(self, index: int) -> bool:
        return (
            index + 1 < len(self._tokens)
            and self._tokens[index + 1].type == TokenType.OPERATOR
            and self._tokens[index + 1].raw == "="
        )

    def _check_assignments(self) -> None:
        assignment_positions = [
            index
            for index, token in enumerate(self._tokens)
            if token.type == TokenType.OPERATOR and token.raw == "="
        ]
        is_simple_assignment = (
            len(assignment_positions) == 1
            and assignment_positions[0] == 1
            and self._tokens[0].type == TokenType.IDENTIFIER
        )
        if assignment_positions and not is_simple_assignment:
            raise InvalidOperatorSequenceError(ERROR_INVALID_EXPRESSION)
