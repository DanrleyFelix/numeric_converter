from typing import Protocol
from numbers import Number
from src.core.command_window.tokenizer.token import Token
from src.core.command_window.validator.validator import ValidationState
from src.modules.utils import COLOR


class IEvaluator(Protocol):

    def evaluate(self, tokens: list[Token]) -> Number:
        pass


class IExpressionValidator(Protocol):
    
    @staticmethod
    def validate(expr: str) -> ValidationState:
        pass


class IEvaluatorUseCase(Protocol):

    def handle(self, tokens: list[Token]) -> Number:
        pass


class ICommandWindowController(Protocol):

    def on_input_changed(self, raw_input: str) -> bool:
        pass

    def on_confirm(self, validation_state: bool, expression: list[Token]) -> Number | None:
        pass


class ICommandWindowView(Protocol):

    def handle_typing(self, text: str) -> tuple[list[str], COLOR]:
        pass

    def handle_enter(self, text: str) -> tuple[list[str], COLOR]:
        pass