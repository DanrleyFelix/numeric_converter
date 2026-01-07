from src.core.command_window.evaluator.errors import EvaluationError, DivisionByZeroError
from numbers import Number
import operator

_BIN_OPS = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": lambda a, b: _safe_div(a, b),
    "%": lambda a, b: _safe_mod(a, b),
    "**": operator.pow,
    "<<": lambda a, b: int(a) << int(b),
    ">>": lambda a, b: int(a) >> int(b),
    "&": lambda a, b: int(a) & int(b),
    "|": lambda a, b: int(a) | int(b),
    "^": lambda a, b: int(a) ^ int(b),
    "==": lambda a, b: int(a == b),
    "!=": lambda a, b: int(a != b),
    "<": lambda a, b: int(a < b),
    "<=": lambda a, b: int(a <= b),
    ">": lambda a, b: int(a > b),
    ">=": lambda a, b: int(a >= b),
    "&&": lambda a, b: int(a) and int(b),
    "||": lambda a, b: int(a) or int(b),
    "=": lambda a, b: b}

def _safe_div(a: Number, b: Number) -> Number:
    if b == 0:
        raise DivisionByZeroError("Division by zero.")
    result = a / b
    return int(result) if result.is_integer() else result

def _safe_mod(a: Number, b: Number) -> Number:
    if b == 0:
        raise DivisionByZeroError("Modulo by zero.")
    return a % b

def apply_operator(operator_str: str, a: Number, b: Number | None = None) -> Number:
    if b is None:
        if operator_str == "!":
            return int(not a)
        if operator_str == "~":
            return int(~a)
        if operator_str == "NEG":
            return -a
        if operator_str == "POS":
            return a
        raise EvaluationError(f"Unknown unary operator '{operator_str}'")
    
    if operator_str in _BIN_OPS:
        return _BIN_OPS[operator_str](a, b)
    
    raise EvaluationError(f"Unknown operator '{operator_str}'")
