from __future__ import annotations

from dataclasses import dataclass

from src.core.command_window.textual_operator_context import previous_allows_unary
from src.core.command_window.tokenizer import Token, TokenType, Tokenizer
from src.modules.command_window_dtos import CommandLogPreferencesDTO


@dataclass(frozen=True)
class CommandLogProfile:
    has_assignment: bool = False
    assignment_only: bool = False
    no_operator: bool = False
    single_unary_only: bool = False
    binary_operator_count: int = 0


_UNARY_OPERATORS = {"+", "-", "~"}


def should_store_command_log(
    expression: str,
    preferences: CommandLogPreferencesDTO,
) -> bool:
    if not preferences.enabled:
        return False

    profile = command_log_profile(expression)
    if preferences.binary_operator_only:
        return profile.binary_operator_count > 0

    if profile.assignment_only:
        return preferences.assignment_only or preferences.assignment_operator
    if profile.has_assignment:
        return preferences.assignment_operator
    if profile.single_unary_only:
        return preferences.single_unary_only
    if profile.no_operator:
        return preferences.no_operator
    return True


def command_log_profile(expression: str) -> CommandLogProfile:
    tokens = _safe_tokens(expression)
    operators = [
        (index, token)
        for index, token in enumerate(tokens)
        if token.type == TokenType.OPERATOR
    ]
    if not operators:
        return CommandLogProfile(no_operator=True)

    assignments = [token for _, token in operators if token.raw == "="]
    unary_count = sum(
        1
        for index, token in operators
        if _is_unary_operator(tokens, index, token)
    )
    binary_count = sum(
        1
        for index, token in operators
        if token.raw != "=" and not _is_unary_operator(tokens, index, token)
    )
    return CommandLogProfile(
        has_assignment=bool(assignments),
        assignment_only=len(operators) == 1 and bool(assignments),
        single_unary_only=len(operators) == 1 and unary_count == 1,
        binary_operator_count=binary_count,
    )


def _is_unary_operator(tokens: list[Token], index: int, token: Token) -> bool:
    previous = tokens[index - 1] if index > 0 else None
    return token.raw in _UNARY_OPERATORS and previous_allows_unary(previous)


def _safe_tokens(expression: str) -> list[Token]:
    try:
        return [
            token
            for token in Tokenizer(expression).tokenize()
            if token.type != TokenType.EOF
        ]
    except Exception:
        return []
