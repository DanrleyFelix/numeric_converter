from __future__ import annotations

from src.core.command_window.tokenizer import Token, TokenType, Tokenizer, TokenizerError
from src.core.command_window.validator.errors import UnknownTokenError
from src.core.command_window.validator.partial_expression_analyzer import PartialExpressionAnalyzer
from src.core.command_window.validator.semantic_validator import SemanticValidator
from src.core.command_window.validator.sequence_validator import SequenceValidator
from src.core.command_window.validator.structure_validator import StructureValidator
from src.core.command_window.validator.validation_state import ValidationState
from src.core.constants import ERROR_INVALID_EXPRESSION


class TokenizerAdapter:
    def __init__(self, expr: str):
        self._expr = expr

    def tokenize(self) -> list[Token]:
        try:
            return Tokenizer(self._expr).tokenize()
        except TokenizerError as error:
            raise UnknownTokenError(ERROR_INVALID_EXPRESSION) from error


class ExpressionChecker:
    def __init__(self, tokens: list[Token]):
        self._tokens = tokens

    def check(self) -> ValidationState:
        return (
            StructureValidator(self._tokens).validate()
            & SequenceValidator(self._tokens).validate()
            & SemanticValidator(self._tokens).validate()
        )


class ExpressionValidator:
    @staticmethod
    def validate(expr: str) -> ValidationState:
        if not expr.strip():
            return ValidationState.POTENTIALLY_INVALID
        if PartialExpressionAnalyzer(expr).is_partial():
            return ValidationState.POTENTIALLY_INVALID
        tokens = [token for token in TokenizerAdapter(expr).tokenize() if token.type != TokenType.EOF]
        return ExpressionChecker(tokens).check()
