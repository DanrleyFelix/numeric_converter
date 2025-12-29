from src.models.command_window.evaluator.errors import (EvaluationError,DivisionByZeroError)
from typing import Union

Number = Union[int, float]

def apply_operator(operator: str, a: Number, b: Number | None = None) -> Number:
    if b is None:
        if operator == "!":
            return 0 if a else 1
        if operator == "~":
            return ~int(a)
        if operator == "-":
            return -a
        raise EvaluationError(f"Unknown unary operator '{operator}'")

    if operator == "+":
        return a + b
    if operator == "-":
        return a - b
    if operator == "*":
        return a * b
    if operator == "/":
        if b == 0:
            raise DivisionByZeroError("Division by zero.")
        result = a / b
        return int(result) if result.is_integer() else result
    if operator == "%":
        if b == 0:
            raise DivisionByZeroError("Modulo by zero.")
        return a % b
    if operator == "**":
        return a ** b
    if operator == "==":
        return 1 if a == b else 0
    if operator == "!=":
        return 1 if a != b else 0
    if operator == "<":
        return 1 if a < b else 0
    if operator == "<=":
        return 1 if a <= b else 0
    if operator == ">":
        return 1 if a > b else 0
    if operator == ">=":
        return 1 if a >= b else 0
    if operator == "<<":
        return int(a) << int(b)
    if operator == ">>":
        return int(a) >> int(b)
    if operator == "&":
        return int(a) & int(b)
    if operator == "|":
        return int(a) | int(b)
    if operator == "^":
        return int(a) ^ int(b)
    if operator == "&&":
        return 1 if (a and b) else 0
    if operator == "||":
        return 1 if (a or b) else 0
    if operator == "=":
        return b

    raise EvaluationError(f"Unknown operator '{operator}'")

