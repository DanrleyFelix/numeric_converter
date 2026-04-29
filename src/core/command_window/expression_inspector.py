from __future__ import annotations

from collections.abc import Mapping, Sequence

from src.core.command_window.tokenizer import Token, TokenType, Tokenizer

_EXCLUDED_ASSIGNMENT_NAMES = {"ANS"}


def is_standalone_identifier_fragment(text: str) -> bool:
    tokens = _safe_tokens(text)
    return len(tokens) == 1 and tokens[0].type == TokenType.IDENTIFIER


def has_trailing_identifier_fragment(text: str, error_position: int) -> bool:
    stripped = text.rstrip()
    if not stripped:
        return False

    tokens = _safe_tokens(stripped)
    if not tokens:
        return False

    last = tokens[-1]
    if last.type != TokenType.IDENTIFIER:
        return False
    if error_position != last.position:
        return False

    return last.position + len(str(last.raw)) == len(stripped)


def extract_assignment_name(text: str) -> str | None:
    tokens = _safe_tokens(text)
    if (
        len(tokens) >= 3
        and tokens[0].type == TokenType.IDENTIFIER
        and tokens[1].type == TokenType.OPERATOR
        and tokens[1].raw == "="
    ):
        return str(tokens[0].raw)
    return None


def ordered_assignment_names(
    instructions: Sequence[str],
    variables: Mapping[str, object],
) -> list[str]:
    ordered_names: list[str] = []

    for instruction in instructions:
        name = extract_assignment_name(instruction)
        if not name or name in _EXCLUDED_ASSIGNMENT_NAMES or name not in variables:
            continue
        if name in ordered_names:
            ordered_names.remove(name)
        ordered_names.append(name)

    for name in variables:
        if name in _EXCLUDED_ASSIGNMENT_NAMES or name in ordered_names:
            continue
        ordered_names.append(name)

    return ordered_names


def _safe_tokens(text: str) -> list[Token]:
    try:
        return [
            token
            for token in Tokenizer(text).tokenize()
            if token.type != TokenType.EOF
        ]
    except Exception:
        return []
