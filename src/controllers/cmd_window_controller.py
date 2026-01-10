from numbers import Number
from typing import List

from src.core.command_window.tokenizer import Tokenizer, Token
from src.application.contracts.cmd_window_contract import (
    IExpressionValidator,
    IEvaluatorUseCase)
from src.application.contracts.cmd_window_contract import ValidationState


class CommandWindowController:

    def __init__(
        self,
        validator: IExpressionValidator,
        evaluator_use_case: IEvaluatorUseCase):

        self._validator = validator
        self._evaluator = evaluator_use_case
        self._tokens: List[Token] = []
        self._validation_state: ValidationState = ValidationState.POTENTIALLY_INVALID

    def on_input_changed(self, raw_input: str) -> ValidationState:

        tokenizer = Tokenizer(raw_input)
        tokens = tokenizer.tokenize(raw_input)
        state = self._validator.validate(tokens)
        self._tokens = tokens
        self._validation_state = state
        return state

    def on_confirm(self) -> Number | None:
        if self._validation_state is not ValidationState.ACCEPTABLE:
            return None
        return self._evaluator.handle(self._tokens)
