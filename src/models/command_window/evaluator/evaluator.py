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
                self._process_operator(token, operators, values)
            elif token.type == TokenType.LPAREN:
                operators.append(token)
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

    def _apply_top_operator(self, operators: List[Token], values: List[Number]) -> None:
        op_token = operators.pop()
        op = op_token.raw
        arity = self._arity(op)

        if arity == 1:
            a = values.pop()
            result = apply_operator(op, a)
        else:
            b = values.pop() # em operações unárias, pode não existir (corrigir quando acordar)
            a = values.pop()
            result = apply_operator(op, a, b)

        values.append(result)

    def _process_operator(self, token: Token, operators: List[Token], values: List[Number]) -> None:
        op = token.raw
        while operators:
            top_token = operators[-1]
            if top_token.type == TokenType.LPAREN:
                break
            top_op = top_token.raw
            reduce_top = (self._precedence(top_op) > self._precedence(op) or
                          (self._precedence(top_op) == self._precedence(op) and self._associativity(op) == Assoc.LEFT))
            if reduce_top:
                self._apply_top_operator(operators, values)
            else:
                break
        operators.append(token)

    def _process_rparen(self, operators: List[Token], values: List[Number]) -> None:
        while operators and operators[-1].type != TokenType.LPAREN:
            self._apply_top_operator(operators, values)
        operators.pop()  # remove "("

    def _finalize(self, operators: List[Token], values: List[Number]) -> None:
        while operators:
            self._apply_top_operator(operators, values)
