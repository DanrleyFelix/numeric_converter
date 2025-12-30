from typing import Union, List
from src.models.constants import OPERATOR_INFO, ASSOC
from src.models.command_window.tokenizer import Token, TokenType
from src.models.command_window.evaluator.apply_operator import apply_operator
from src.models.command_window.evaluator.errors import EvaluationError

Number = Union[int, float]


class Evaluator:

    def evaluate(self, tokens: List[Token]) -> Number:
        stack = _EvaluationStack()
        prev_token: Token | None = None
        for token in tokens:
            match token.type:
                case TokenType.NUMBER:
                    stack.push_value(token.value)
                case TokenType.OPERATOR:
                    token = self._normalize_unary(token, prev_token)
                    stack.push_operator(token)
                case TokenType.LPAREN:
                    stack.push_lparen(token)
                case TokenType.RPAREN:
                    stack.reduce_until_lparen()
                case TokenType.EOF:
                    break
            prev_token = token
        stack.finalize()
        return stack.result()

    def _normalize_unary(self, token: Token, prev_token: Token | None) -> Token:
        if token.raw in ("+", "-"):
            if prev_token is None or prev_token.type in {TokenType.OPERATOR, TokenType.LPAREN}:
                token = Token(TokenType.OPERATOR, "POS" if token.raw == "+" else "NEG")
        return token


class _EvaluationStack:

    def __init__(self):
        self._values: List[Number] = []
        self._operators: List[Token] = []

    def push_value(self, value: Number) -> None:
        self._values.append(value)

    def push_lparen(self, token: Token) -> None:
        self._operators.append(token)

    def push_operator(self, token: Token) -> None:
        while self._operators and self._should_reduce(self._operators[-1], token):
            self._apply(self._operators.pop())
        self._operators.append(token)

    def reduce_until_lparen(self) -> None:
        while self._operators and self._operators[-1].type != TokenType.LPAREN:
            self._apply(self._operators.pop())
        if not self._operators:
            raise EvaluationError("Mismatched parentheses")
        self._operators.pop()

    def finalize(self) -> None:
        while self._operators:
            self._apply(self._operators.pop())

    def result(self) -> Number:
        if len(self._values) != 1:
            raise EvaluationError("Invalid expression")
        return self._values[0]

    def _should_reduce(self, top: Token, current: Token) -> bool:
        if top.type == TokenType.LPAREN: return False

        top_prec, _, top_assoc = OPERATOR_INFO[top.raw]
        cur_prec, _, _ = OPERATOR_INFO[current.raw]

        if top_prec > cur_prec: return True
        if top_prec == cur_prec and top_assoc == ASSOC.LEFT: return True
        return False


    def _apply(self, token: Token) -> None:
        _, arity, _ = OPERATOR_INFO[token.raw]

        if arity == 1:
            if not self._values:
                raise EvaluationError(f"Unary operator '{token.raw}' without operand")
            a = self._values.pop()
            self._values.append(apply_operator(token.raw, a))
        elif arity == 2:
            if len(self._values) < 2:
                raise EvaluationError(f"Binary operator '{token.raw}' without enough operands")
            b = self._values.pop()
            a = self._values.pop()
            self._values.append(apply_operator(token.raw, a, b))
