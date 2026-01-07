from typing import List
from numbers import Number
from src.core.command_window.tokenizer import Token, TokenType
from src.application.contracts.cmd_window_contract import IEvaluator
from src.core.command_window.context import cmd_window_context


class EvaluatorUseCase:

    def __init__(self, evaluator: IEvaluator):
        self.evaluator = evaluator

    def handle(self, tokens: List[Token]) -> Number:
        lhs, rhs_tokens = self._split_assignment(tokens)
        resolved_rhs = self._resolve_identifiers(rhs_tokens)
        result = self.evaluator.evaluate(resolved_rhs)
        if lhs is not None:
            cmd_window_context.set_variable(lhs, result)
        else:
            cmd_window_context.set_variable("ANS", result)
        return result

    def _split_assignment(self, tokens: List[Token]) -> tuple[str | None, List[Token]]:
        for i, t in enumerate(tokens):
            if t.type == TokenType.OPERATOR and t.raw == "=":
                lhs = tokens[i - 1].raw
                rhs = tokens[i + 1 :]
                return lhs, rhs
        return None, tokens

    def _resolve_identifiers(self, tokens: List[Token]) -> List[Token]:
        resolved: List[Token] = []
        for t in tokens:
            if t.type == TokenType.IDENTIFIER:
                value = cmd_window_context.get_variable(t.raw)
                resolved.append(
                    Token(
                        type=TokenType.NUMBER,
                        raw=t.raw,
                        value=value,
                        position=t.position))
            else:
                resolved.append(t)
        return resolved
