from __future__ import annotations

from src.core.command_window.textual_operator_context import (
    binary_left_delimited,
    binary_right_delimited,
    character_after_range,
    character_before,
    next_allows_operand,
    previous_allows_binary,
    previous_allows_unary,
    unary_left_delimited,
    unary_right_delimited,
)
from src.core.command_window.tokenizer.token import Token, TokenType
from src.core.constants import TEXTUAL_OPERATORS


class TextualOperatorNormalizer:
    def __init__(self, text: str, tokens: list[Token]):
        self._text = text
        self._tokens = tokens

    def normalize(self) -> list[Token]:
        normalized: list[Token] = []
        for index, token in enumerate(self._tokens):
            normalized.append(self._normalize_token(index, token))
        return normalized

    def _normalize_token(self, index: int, token: Token) -> Token:
        if token.type is not TokenType.IDENTIFIER:
            return token

        alias = token.raw.upper()
        operator = TEXTUAL_OPERATORS.get(alias)
        if operator is None:
            return token

        previous = self._tokens[index - 1] if index > 0 else None
        next_token = self._tokens[index + 1] if index + 1 < len(self._tokens) else None

        if alias == "NOT" and self._is_unary_operator(token, previous, next_token):
            return Token(TokenType.OPERATOR, operator, operator, token.position)
        if alias != "NOT" and self._is_binary_operator(token, previous, next_token):
            return Token(TokenType.OPERATOR, operator, operator, token.position)
        return token

    def _is_unary_operator(self, token: Token, previous: Token | None, next_token: Token | None) -> bool:
        before = character_before(self._text, token.position)
        after = character_after_range(self._text, token.position, len(token.raw))
        return (
            previous_allows_unary(previous)
            and next_allows_operand(next_token, allow_none=True)
            and unary_left_delimited(before)
            and unary_right_delimited(after, allow_end=False)
        )

    def _is_binary_operator(self, token: Token, previous: Token | None, next_token: Token | None) -> bool:
        before = character_before(self._text, token.position)
        after = character_after_range(self._text, token.position, len(token.raw))
        return (
            previous_allows_binary(previous)
            and next_allows_operand(next_token, allow_none=True)
            and binary_left_delimited(before)
            and binary_right_delimited(after, allow_end=False)
        )
