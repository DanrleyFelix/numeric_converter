from typing import List

from src.models.constants import ERROR_INVALID_EXPRESSION, UNARY_OPERATORS, SIGNALS
from src.models.command_window.tokenizer import (
    Tokenizer,
    TokenizerError,
    TokenType,
    Token)
from src.models.command_window.validator.errors import (
    InvalidStartError,
    InvalidOperatorSequenceError,
    ParenthesisMismatchError,
    UnknownTokenError,
    UnknownVariableError)
from src.models.command_window.context import Context


class ValidationState:
    POTENTIALLY_INVALID = 0
    ACCEPTABLE = 1


class ExpressionValidator:

    @staticmethod
    def validate(expr: str, ctx: Context) -> ValidationState:
        if not expr.strip():
            return ValidationState.POTENTIALLY_INVALID

        tokens = ExpressionValidator._tokenize(expr)
        tokens = [t for t in tokens if t.type != TokenType.EOF]

        state = ValidationState.ACCEPTABLE
        state &= ExpressionValidator._check_start(tokens)
        state &= ExpressionValidator._check_parentheses(tokens)
        state &= ExpressionValidator._check_tokens_sequence(tokens)
        state &= ExpressionValidator._check_variable_usage(tokens, ctx)
        state &= ExpressionValidator._check_assignment_rules(tokens)
        state &= ExpressionValidator._check_partial_state(tokens)

        return state

    @staticmethod
    def _tokenize(expr: str) -> List[Token]:
        try:
            return Tokenizer(expr).tokenize()
        except TokenizerError as e:
            raise UnknownTokenError(ERROR_INVALID_EXPRESSION) from e

    @staticmethod
    def _check_start(tokens: List[Token]) -> ValidationState:
        first = tokens[0]

        if first.type == TokenType.OPERATOR and first.raw not in SIGNALS:
            if first.raw not in UNARY_OPERATORS:
                raise InvalidStartError(ERROR_INVALID_EXPRESSION, position=first.position)

        return ValidationState.ACCEPTABLE

    @staticmethod
    def _check_parentheses(tokens: List[Token]) -> ValidationState:
        balance = 0
        for t in tokens:
            if t.type == TokenType.LPAREN:
                balance += 1
            elif t.type == TokenType.RPAREN:
                balance -= 1
                if balance < 0:
                    raise ParenthesisMismatchError(ERROR_INVALID_EXPRESSION, position=t.position)

        if balance > 0:
            return ValidationState.POTENTIALLY_INVALID

        return ValidationState.ACCEPTABLE

    @staticmethod
    def _check_tokens_sequence(tokens: List[Token]) -> ValidationState:
        for prev, curr in zip(tokens, tokens[1:]):
            prev_is_operator = prev.type == TokenType.OPERATOR
            curr_is_operator = curr.type == TokenType.OPERATOR
            curr_is_rparen = curr.type == TokenType.RPAREN
            prev_is_lparen = prev.type == TokenType.LPAREN
            curr_is_lparen = curr.type == TokenType.LPAREN
            prev_is_operand = prev.type in {TokenType.NUMBER, TokenType.IDENTIFIER}

            two_operators_in_sequence = prev_is_operator and curr_is_operator
            operator_before_rparen = prev_is_operator and curr_is_rparen
            empty_parentheses = prev_is_lparen and curr_is_rparen
            implicit_multiplication = prev_is_operand and curr_is_lparen

            if two_operators_in_sequence:
                if curr.raw in UNARY_OPERATORS or curr.raw in SIGNALS:
                    continue
                raise InvalidOperatorSequenceError(ERROR_INVALID_EXPRESSION,position=curr.position)

            if operator_before_rparen:
                raise InvalidOperatorSequenceError(ERROR_INVALID_EXPRESSION,position=curr.position)

            if empty_parentheses:
                raise ParenthesisMismatchError(ERROR_INVALID_EXPRESSION,position=curr.position)

            if implicit_multiplication:
                raise InvalidOperatorSequenceError(ERROR_INVALID_EXPRESSION,position=curr.position)

        return ValidationState.ACCEPTABLE

    @staticmethod
    def _check_variable_usage(tokens: List[Token], ctx: Context) -> ValidationState:
        for i, t in enumerate(tokens):
            if t.type != TokenType.IDENTIFIER:
                continue

            is_lhs = (i + 1 < len(tokens) and tokens[i + 1].type == TokenType.OPERATOR and tokens[i + 1].raw == "=")

            if not is_lhs and ctx.get_variable(t.raw) is None:
                raise UnknownVariableError(f"Variable '{t.raw}' is not defined.", position=t.position)

        return ValidationState.ACCEPTABLE

    @staticmethod
    def _check_assignment_rules(tokens: List[Token]) -> ValidationState:
        assignments = [t for t in tokens if t.type == TokenType.OPERATOR and t.raw == "="]

        if len(assignments) > 1:
            raise InvalidOperatorSequenceError(ERROR_INVALID_EXPRESSION)

        if assignments:
            if tokens[0].type != TokenType.IDENTIFIER:
                raise InvalidOperatorSequenceError(ERROR_INVALID_EXPRESSION)

        return ValidationState.ACCEPTABLE

    @staticmethod
    def _check_partial_state(tokens: List[Token]) -> ValidationState:
        if not tokens:
            return ValidationState.POTENTIALLY_INVALID

        last = tokens[-1]

        if last.type == TokenType.OPERATOR:
            return ValidationState.POTENTIALLY_INVALID

        if last.type == TokenType.LPAREN:
            return ValidationState.POTENTIALLY_INVALID

        return ValidationState.ACCEPTABLE
