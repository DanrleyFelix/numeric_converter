import math
from src.models.command_window.evaluator.errors import (EvaluationError,DivisionByZeroError, InvalidUnaryOperationError)
from typing import Union

Number = Union[int, float]

def apply_operator(operator: str, a: Number, b: Number | None = None) -> Number:
    try:
        if operator == "!":
            return 0 if a else 1

        if operator == "~":
            return ~int(a)

        if operator == "sqrt":
            if a < 0:
                raise InvalidUnaryOperationError("Square root of negative number.")
            result = math.sqrt(a)
            return int(result) if result.is_integer() else result

        if b is None:
            raise EvaluationError(f"Missing operand for operator '{operator}'")

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
                raise DivisionByZeroError("Module by zero.")
            return a % b

        if operator == "**":
            return a ** b

        if operator == "==":
            return 1 if a == b else 0

        if operator == "!=":
            return 1 if a != b else 0

        if operator == "<":
            return 1 if a < b else 0

        if operator == ">":
            return 1 if a > b else 0

        if operator == "<=":
            return 1 if a <= b else 0

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

    except EvaluationError:
        raise
    except Exception as e:
        raise EvaluationError(str(e)) from e
