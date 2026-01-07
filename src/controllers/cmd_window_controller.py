from typing import List
from numbers import Number
from src.core.command_window.tokenizer import Tokenizer, Token
from src.application.contracts.cmd_window_contract import IExpressionValidator
from src.application.contracts.cmd_window_contract import IEvaluatorUseCase


class CommandWindowController:

    def __init__(self, tokenizer: Tokenizer, validator: IExpressionValidator, evaluator_use_case: IEvaluatorUseCase):
        self.tokenizer = tokenizer
        self.validator = validator
        self.evaluator_use_case = evaluator_use_case

    def on_input_changed(self, raw_input: str) -> bool:
        tokens = self.tokenizer.tokenize(raw_input)
        state = self.validator.validate(tokens)
        return state 

    def on_confirm(self, validation_state: bool, expression: List[Token]) -> Number | None:
        if validation_state:
            return self.evaluator_use_case.handle(expression)
        else:
            return None
