from __future__ import annotations

from src.core.command_window.tokenizer.token import Token, TokenType

TEXTUAL_OPERATOR_CHARS = frozenset("+-*/%<>=!&|^~")
UNARY_PREVIOUS_TYPES = frozenset({TokenType.OPERATOR, TokenType.LPAREN})
BINARY_PREVIOUS_TYPES = frozenset({
    TokenType.NUMBER,
    TokenType.IDENTIFIER,
    TokenType.RPAREN,
})
OPERAND_START_TYPES = frozenset({
    TokenType.NUMBER,
    TokenType.IDENTIFIER,
    TokenType.LPAREN,
})


def character_before(text: str, position: int) -> str | None:
    if position <= 0:
        return None
    return text[position - 1]


def character_after_range(text: str, start: int, length: int) -> str | None:
    position = start + length
    if position >= len(text):
        return None
    return text[position]


def unary_left_delimited(character: str | None) -> bool:
    return (
        character is None
        or character.isspace()
        or character == "("
        or character in TEXTUAL_OPERATOR_CHARS
    )


def unary_right_delimited(character: str | None, allow_end: bool) -> bool:
    if character is None:
        return allow_end
    return character.isspace() or character == "("


def binary_left_delimited(character: str | None) -> bool:
    return character is not None and (character.isspace() or character == ")")


def binary_right_delimited(character: str | None, allow_end: bool) -> bool:
    if character is None:
        return allow_end
    return character.isspace() or character == "("


def previous_allows_unary(previous: Token | None) -> bool:
    return previous is None or previous.type in UNARY_PREVIOUS_TYPES


def previous_allows_binary(previous: Token | None) -> bool:
    return previous is not None and previous.type in BINARY_PREVIOUS_TYPES


def next_allows_operand(next_token: Token | None, allow_none: bool) -> bool:
    if next_token is None:
        return allow_none
    return next_token.type in OPERAND_START_TYPES
