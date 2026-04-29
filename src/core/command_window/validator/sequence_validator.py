from __future__ import annotations

from src.core.command_window.tokenizer import Token, TokenType
from src.core.command_window.validator.errors import (
    InvalidOperatorSequenceError,
    ParenthesisMismatchError,
)
from src.core.command_window.validator.validation_state import ValidationState
from src.core.constants import (
    ARITHMETIC_OPERATORS,
    ASSIGNMENT_OPERATOR,
    CONDITIONAL_OPERATORS,
    ERROR_INVALID_EXPRESSION,
    UNARY_OPERATORS,
)


class SequenceValidator:
    def __init__(self, tokens: list[Token]):
        self._tokens = tokens

    def validate(self) -> ValidationState:
        for index in range(len(self._tokens) - 1):
            self._validate_pair(index)
        return ValidationState.ACCEPTABLE

    def _validate_pair(self, index: int) -> None:
        previous = self._tokens[index]
        current = self._tokens[index + 1]

        if previous.type == TokenType.OPERATOR and current.type == TokenType.RPAREN:
            self._raise_operator_error(current)
        if previous.type == TokenType.LPAREN and current.type == TokenType.RPAREN:
            self._raise_parenthesis_error(current)
        if self._is_implicit_multiplication(previous, current):
            self._raise_operator_error(current)
        if self._is_invalid_operator_sequence(index):
            self._raise_operator_error(current)

    def _is_implicit_multiplication(self, previous: Token, current: Token) -> bool:
        left_types = {TokenType.NUMBER, TokenType.IDENTIFIER, TokenType.RPAREN}
        right_types = {TokenType.NUMBER, TokenType.IDENTIFIER, TokenType.LPAREN}
        return previous.type in left_types and current.type in right_types

    def _is_invalid_operator_sequence(self, index: int) -> bool:
        previous = self._tokens[index]
        current = self._tokens[index + 1]
        if previous.type != TokenType.OPERATOR or current.type != TokenType.OPERATOR:
            return False
        if current.raw not in UNARY_OPERATORS:
            return True
        if previous.raw in UNARY_OPERATORS:
            return True
        if current.raw in {"+", "-"}:
            allowed_previous = ARITHMETIC_OPERATORS | ASSIGNMENT_OPERATOR | CONDITIONAL_OPERATORS
            return previous.raw not in allowed_previous
        return index + 2 >= len(self._tokens) or self._tokens[index + 2].type not in {
            TokenType.NUMBER,
            TokenType.IDENTIFIER,
            TokenType.LPAREN,
        }

    def _raise_operator_error(self, token: Token) -> None:
        raise InvalidOperatorSequenceError(ERROR_INVALID_EXPRESSION, position=token.position)

    def _raise_parenthesis_error(self, token: Token) -> None:
        raise ParenthesisMismatchError(ERROR_INVALID_EXPRESSION, position=token.position)
