from typing import Union, List
from src.models.constants import OPERATOR_INFO, Assoc
from src.models.command_window.tokenizer import Token, TokenType
from src.models.command_window.evaluator.apply_operator import apply_operator
from src.models.command_window.evaluator.errors import EvaluationError

Number = Union[int, float]


class Evaluator:

    def evaluate(self, tokens: List[Token]) -> Number:
        values: List[Number] = []
        operators: List[str] = []

        for token in tokens:
            if token.type == TokenType.NUMBER:
                values.append(token.value)
            elif token.type == TokenType.OPERATOR:
                self._process_operator(token.raw, operators, values)
            elif token.type == TokenType.LPAREN:
                operators.append("(")
            elif token.type == TokenType.RPAREN:
                self._process_rparen(operators, values)
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

    def _apply_top_operator(self, operators: List[str], values: List[Number]) -> None:
        op = operators.pop()
        op_arity = self._arity(op)

        if op_arity == 1:
            a = values.pop()
            result = apply_operator(op, a)
        else:
            b = values.pop()
            a = values.pop()
            result = apply_operator(op, a, b)

        values.append(result)

    def _process_operator(self, op: str, operators: List[str], values: List[Number]) -> None:
        while operators:
            top = operators[-1]
            if top == "(":
                break
            reduce_top = (self._precedence(top) > self._precedence(op) or
                          (self._precedence(top) == self._precedence(op) and self._associativity(op) == Assoc.LEFT))
            if reduce_top:
                self._apply_top_operator(operators, values)
            else:
                break
        operators.append(op)

    def _process_rparen(self, operators: List[str], values: List[Number]) -> None:
        while operators and operators[-1] != "(":
            self._apply_top_operator(operators, values)
        if not operators:
            raise EvaluationError("Mismatched parentheses")
        operators.pop()

    def _finalize(self, operators: List[str], values: List[Number]) -> None:
        while operators:
            if operators[-1] == "(":
                raise EvaluationError("Mismatched parentheses")
            self._apply_top_operator(operators, values)
