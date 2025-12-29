from typing import Union, List
from src.models.constants import OPERATOR_INFO, Assoc
from src.models.command_window.tokenizer import Token, TokenType
from src.models.command_window.evaluator.apply_operator import apply_operator
from src.models.command_window.evaluator.errors import EvaluationError

Number = Union[int, float]


class Evaluator:

    def evaluate(self, tokens: List[Token]) -> Number:
        values: List[Number] = []
        operators: List[Token] = []

        for token in tokens:
            if token.type == TokenType.NUMBER:
                values.append(token.value)
            elif token.type == TokenType.OPERATOR:
                self._handle_operator(token, operators, values)
            elif token.type == TokenType.LPAREN:
                operators.append(token)
            elif token.type == TokenType.RPAREN:
                self._handle_rparen(operators, values)
            elif token.type == TokenType.EOF:
                break

        self._finalize(operators, values)

        if len(values) != 1:
            raise EvaluationError("Invalid evaluation state")

        return values[0]

    def _precedence(self, op: str) -> int:
        return OPERATOR_INFO[op][0]

    def _associativity(self, op: str) -> Assoc:
        return OPERATOR_INFO[op][2]

    def _arity(self, op: str) -> int:
        return OPERATOR_INFO[op][1]

    def _handle_operator(self, token: Token, operators: List[Token], values: List[Number]) -> None:
        while operators:
            top = operators[-1]
            if top.type == TokenType.LPAREN:
                break

            top_op = top.raw
            top_prec = self._precedence(top_op)
            token_prec = self._precedence(token.raw)

            reduce_top = (
                top_prec > token_prec or
                (top_prec == token_prec and self._associativity(token.raw) == Assoc.LEFT))

            if reduce_top:
                self._apply_operator_token(operators.pop(), values)
            else:
                break

        operators.append(token)

    def _apply_operator_token(self, token: Token, values: List[Number]) -> None:
        arity = 1 if getattr(token, "is_unary", False) else 2

        if arity == 1:
            if not values:
                raise EvaluationError(f"Missing operand for unary operator '{token.raw}'")
            a = values.pop()
            result = apply_operator(token.raw, a)
        else:
            if len(values) < 2:
                raise EvaluationError(f"Missing operands for binary operator '{token.raw}'")
            b = values.pop()
            a = values.pop()
            result = apply_operator(token.raw, a, b)

        values.append(result)

    def _handle_rparen(self, operators: List[Token], values: List[Number]) -> None:
        while operators and operators[-1].type != TokenType.LPAREN:
            self._apply_operator_token(operators.pop(), values)

        if not operators or operators[-1].type != TokenType.LPAREN:
            raise EvaluationError("Mismatched parentheses")

        operators.pop()

    def _finalize(self, operators: List[Token], values: List[Number]) -> None:
        while operators:
            if operators[-1].type == TokenType.LPAREN:
                raise EvaluationError("Mismatched parentheses")
            self._apply_operator_token(operators.pop(), values)
