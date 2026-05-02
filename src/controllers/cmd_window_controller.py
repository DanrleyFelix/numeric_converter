from numbers import Number
from typing import List

from src.core.command_window.tokenizer import Token, Tokenizer
from src.core.command_window.validator.validator import ValidationState
from src.modules.use_cases import EvaluatorUseCase


class CommandWindowController:
    def __init__(self, validator, evaluator_use_case: EvaluatorUseCase):
        self._validator = validator
        self._evaluator = evaluator_use_case
        self._tokens: List[Token] = []
        self._validation_state: ValidationState = ValidationState.POTENTIALLY_INVALID

    def on_input_changed(self, raw_input: str) -> ValidationState:
        self._tokens = []
        self._validation_state = ValidationState.POTENTIALLY_INVALID
        state = self._validator.validate(raw_input)
        try:
            tokenizer = Tokenizer(raw_input)
            self._tokens = tokenizer.tokenize()
        except Exception:
            self._tokens = []
        self._validation_state = state
        return state

    def on_confirm(self) -> Number | None:
        if self._validation_state is not ValidationState.ACCEPTABLE:
            return None
        return self._evaluator.handle(self._tokens)
