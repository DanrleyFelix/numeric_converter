from numbers import Number

from src.core.command_window.context import cmd_window_context
from src.core.command_window.tokenizer import Token, TokenType
from src.core.converter import Converter


class ConverterUseCase:
    def execute(self, from_type: str, value: str) -> dict[str, object]:
        return Converter.convert(from_type, value)


class EvaluatorUseCase:
    def __init__(self, evaluator) -> None:
        self._evaluator = evaluator

    def handle(self, tokens: list[Token]) -> Number:
        name, rhs_tokens = self._split_assignment(tokens)
        resolved = self._resolve_identifiers(rhs_tokens)
        result = self._evaluator.evaluate(resolved)
        cmd_window_context.set_variable(name or "ANS", result)
        return result

    def _split_assignment(self, tokens: list[Token]) -> tuple[str | None, list[Token]]:
        for index, token in enumerate(tokens):
            if token.type == TokenType.OPERATOR and token.raw == "=":
                return tokens[index - 1].raw, tokens[index + 1 :]
        return None, tokens

    def _resolve_identifiers(self, tokens: list[Token]) -> list[Token]:
        resolved: list[Token] = []
        for token in tokens:
            if token.type != TokenType.IDENTIFIER:
                resolved.append(token)
                continue
            resolved.append(
                Token(
                    type=TokenType.NUMBER,
                    raw=token.raw,
                    value=cmd_window_context.get_variable(token.raw),
                    position=token.position,
                )
            )
        return resolved
