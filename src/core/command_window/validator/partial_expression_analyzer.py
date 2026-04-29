from __future__ import annotations

from src.core.command_window.textual_operator_context import (
    binary_left_delimited,
    character_after_range,
    character_before,
    previous_allows_binary,
    previous_allows_unary,
    unary_left_delimited,
    unary_right_delimited,
)
from src.core.command_window.tokenizer import Token, TokenType, Tokenizer, TokenizerError
from src.core.command_window.validator.errors import ValidationError
from src.core.command_window.validator.sequence_validator import SequenceValidator
from src.core.command_window.validator.structure_validator import StructureValidator
from src.core.constants import BASE_PREFIXES, MULTI_CHAR_OPERATORS, TEXTUAL_OPERATORS


class PartialExpressionAnalyzer:
    def __init__(self, expr: str):
        self._expr = expr

    def is_partial(self) -> bool:
        stripped = self._expr.rstrip()
        if not stripped:
            return True

        trailing = self._trailing_fragment(stripped)
        if not trailing:
            return False
        if trailing != "=" and any(op.startswith(trailing) and op != trailing for op in MULTI_CHAR_OPERATORS):
            return True
        if self._could_be_textual_operator(stripped, trailing):
            return True
        if trailing.lower() in BASE_PREFIXES:
            return True
        return len(trailing) > 1 and any(
            prefix.startswith(trailing.lower()) and prefix != trailing.lower()
            for prefix in BASE_PREFIXES
        )

    def _trailing_fragment(self, text: str) -> str:
        operator_chars = set("+-*/%<>=!&|^~")
        start = len(text)
        while start > 0:
            character = text[start - 1]
            if character.isspace() or character in "()" or character in operator_chars:
                break
            start -= 1
        return text[start:]

    def _could_be_textual_operator(self, text: str, trailing: str) -> bool:
        candidates = [alias for alias in TEXTUAL_OPERATORS if alias.startswith(trailing.upper())]
        if not candidates:
            return False
        prefix_tokens = self._prefix_tokens(text[: len(text) - len(trailing)])
        if prefix_tokens is None or not self._prefix_is_structurally_valid(prefix_tokens):
            return False
        previous = prefix_tokens[-1] if prefix_tokens else None
        start = len(text) - len(trailing)
        before = character_before(text, start)
        after = character_after_range(text, start, len(trailing))
        return any(
            self._candidate_matches(alias, previous, before, after)
            for alias in candidates
        )

    def _candidate_matches(self, alias: str, previous: Token | None, before: str | None, after: str | None) -> bool:
        if alias == "NOT":
            return previous_allows_unary(previous) and unary_left_delimited(before) and unary_right_delimited(after, allow_end=True)
        return previous_allows_binary(previous) and binary_left_delimited(before)

    def _prefix_tokens(self, prefix: str) -> list[Token] | None:
        try:
            return [token for token in Tokenizer(prefix).tokenize() if token.type != TokenType.EOF]
        except TokenizerError:
            return None

    def _prefix_is_structurally_valid(self, tokens: list[Token]) -> bool:
        if not tokens:
            return True
        try:
            StructureValidator(tokens).validate()
            SequenceValidator(tokens).validate()
        except ValidationError:
            return False
        return True
