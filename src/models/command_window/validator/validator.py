from typing import List
from src.models.constants import ERROR_INVALID_EXPRESSION
from src.models.command_window.tokenizer import Tokenizer, TokenizerError, TokenType, Token
from src.models.command_window.validator.errors import (
    InvalidStartError, InvalidOperatorSequenceError,
    ParenthesisMismatchError, UnknownTokenError, UnknownVariableError)
from src.models.command_window.context import Context


class ValidationState:
    POTENTIALLY_INVALID = "potentially_invalid"
    ACCEPTABLE = "acceptable"


class ExpressionValidator:

    @staticmethod
    def validate(expr: str, ctx: Context) -> ValidationState:
        if not expr.strip():
            return ValidationState.POTENTIALLY_INVALID

        tokens = ExpressionValidator._tokenize(expr)
        tokens: List[Token] = [t for t in tokens if t.type != TokenType.EOF]

        ExpressionValidator._check_start(tokens)
        ExpressionValidator._check_parentheses(tokens)
        ExpressionValidator._check_operator_sequences(tokens)
        ExpressionValidator._check_variable_usage(tokens, ctx)

        return ExpressionValidator._check_partial_state(tokens)

    @staticmethod
    def _tokenize(expr: str) -> List:
        try:
            return Tokenizer(expr).tokenize()
        except TokenizerError as e:
            raise UnknownTokenError(ERROR_INVALID_EXPRESSION) from e

    @staticmethod
    def _check_start(tokens: List[Token]):
        first = tokens[0]
        if first.type == TokenType.OPERATOR and not first.can_be_unary:
            raise InvalidStartError(ERROR_INVALID_EXPRESSION, position=first.position)

    @staticmethod
    def _check_parentheses(tokens: List[Token]):
        balance = 0
        for t in tokens:
            if t.type == TokenType.LPAREN:
                balance += 1
            elif t.type == TokenType.RPAREN:
                balance -= 1
                if balance < 0:
                    raise ParenthesisMismatchError(ERROR_INVALID_EXPRESSION, position=t.position)

    @staticmethod
    def _check_operator_sequences(tokens: List[Token]):
        for prev, curr in zip(tokens, tokens[1:]):
            if prev.type == TokenType.OPERATOR and curr.type == TokenType.OPERATOR:
                if curr.can_be_unary:
                    continue
                raise InvalidOperatorSequenceError(ERROR_INVALID_EXPRESSION, position=curr.position)

            if prev.type == TokenType.OPERATOR and curr.type == TokenType.RPAREN:
                raise InvalidOperatorSequenceError(ERROR_INVALID_EXPRESSION, position=curr.position)

            if prev.type == TokenType.LPAREN and curr.type == TokenType.RPAREN:
                raise ParenthesisMismatchError(ERROR_INVALID_EXPRESSION, position=curr.position)

            if prev.type in {TokenType.NUMBER, TokenType.IDENTIFIER} and curr.type == TokenType.LPAREN:
                raise InvalidOperatorSequenceError(ERROR_INVALID_EXPRESSION, position=curr.position)

    @staticmethod
    def _check_variable_usage(tokens: List[Token], ctx: Context):
        for i, t in enumerate(tokens):
            if t.type == TokenType.IDENTIFIER:
                is_lhs = (i + 1 < len(tokens) and tokens[i + 1].type == TokenType.OPERATOR and tokens[i + 1].raw == "=")
                if not is_lhs and ctx.get_variable(t.raw) is None:
                    raise UnknownVariableError(f"Variable '{t.raw}' is not defined.", position=t.position)

    @staticmethod
    def _check_partial_state(tokens: List[Token]) -> ValidationState:
        balance = sum(1 if t.type == TokenType.LPAREN else -1 if t.type == TokenType.RPAREN else 0 for t in tokens)
        last = tokens[-1]
        if balance > 0 or (last.type == TokenType.OPERATOR and not last.can_be_unary):
            return ValidationState.POTENTIALLY_INVALID
        return ValidationState.ACCEPTABLE
