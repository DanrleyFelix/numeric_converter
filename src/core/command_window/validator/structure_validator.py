from __future__ import annotations

from src.core.command_window.tokenizer import Token, TokenType
from src.core.command_window.validator.errors import InvalidStartError, ParenthesisMismatchError
from src.core.command_window.validator.validation_state import ValidationState
from src.core.constants import ERROR_INVALID_EXPRESSION, UNARY_OPERATORS


class StructureValidator:
    def __init__(self, tokens: list[Token]):
        self._tokens = tokens

    def validate(self) -> ValidationState:
        return (
            self._check_start()
            & self._check_parentheses()
            & self._check_partial_syntax()
        )

    def _check_start(self) -> ValidationState:
        first = self._tokens[0]
        if first.type == TokenType.OPERATOR and first.raw not in UNARY_OPERATORS:
            raise InvalidStartError(ERROR_INVALID_EXPRESSION, position=first.position)
        return ValidationState.ACCEPTABLE

    def _check_parentheses(self) -> ValidationState:
        balance = 0
        for token in self._tokens:
            if token.type == TokenType.LPAREN:
                balance += 1
            elif token.type == TokenType.RPAREN:
                balance -= 1
                if balance < 0:
                    raise ParenthesisMismatchError(
                        ERROR_INVALID_EXPRESSION,
                        position=token.position,
                    )
        return ValidationState.POTENTIALLY_INVALID if balance > 0 else ValidationState.ACCEPTABLE

    def _check_partial_syntax(self) -> ValidationState:
        if not self._tokens:
            return ValidationState.POTENTIALLY_INVALID
        if self._tokens[-1].type in {TokenType.OPERATOR, TokenType.LPAREN}:
            return ValidationState.POTENTIALLY_INVALID
        return ValidationState.ACCEPTABLE
