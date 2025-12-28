from typing import List, Union
from src.models.command_window.tokenizer import Token, TokenType
from src.models.command_window.evaluator.evaluator import Evaluator
from src.models.command_window.context import Context


Number = Union[int, float]

class AssignmentHandler:
    def __init__(self, ctx: Context):
        self.ctx = ctx
        self.evaluator = Evaluator()

    def handle(self, tokens: List[Token]) -> Number:
        lhs, rhs_tokens = self._split_assignment(tokens)
        result = self.evaluator.evaluate(rhs_tokens)

        if lhs:
            self.ctx.set_variable(lhs, result)

        self.ctx.set_variable("ANS", result)
        return result

    def _split_assignment(self, tokens: List[Token]) -> tuple[str | None, List[Token]]:

        for i, t in enumerate(tokens):
            if t.type == TokenType.OPERATOR and t.raw == "=":
                lhs = tokens[i-1].raw
                rhs_tokens = tokens[i+1:]
                return lhs, rhs_tokens
        return None, tokens
