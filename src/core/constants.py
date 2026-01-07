import re
from enum import Enum, auto

DECIMAL_DIGITS = "0123456789"
BINARY_DIGITS = "01"
HEX_DIGITS = "0123456789abcdefABCDEF"

OPERATORS = {"+", "-", "*", "/", "%", "**",
    "<<", ">>", "==", "!=", "<", ">", "<=", ">=",
    "&", "|", "^", "~", "&&", "||", "!", "="}
ASSIGNMENT_OPERATOR = {"="}
BITWISE_OPERATORS = {"<<", ">>"}
LOGICAL_OPERATORS = {"&", "|", "^", "~", "&&", "||", "!"}
CONDITIONAL_OPERATORS = {"==", "!=", "<", ">", "<=", ">="}
ARITHMETIC_OPERATORS = {"*", "-", "+", "/", "**"}
UNARY_OPERATORS = {"!", "~", "+", "-"}
BASE_PREFIXES = {"0b": 2, "0x": 16}

MULTI_CHAR_OPERATORS = sorted(OPERATORS, key=len, reverse=True)

ERROR_INVALID_EXPRESSION = ("Invalid expression. Use BACKSPACE or X key to delete it.")
ERROR_DIVISION_BY_ZERO = "Division by zero."
ERROR_UNKNOWN_TOKEN = "Unknown token."

IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
WHITESPACE_RE = re.compile(r"\s+")

class ASSOC(Enum):
    LEFT = auto()
    RIGHT = auto()

# operator : (precedence, arity, Associativity)
OPERATOR_INFO = {
    "=":   (1, 2, ASSOC.RIGHT),

    "||":  (2, 2, ASSOC.LEFT),
    "&&":  (3, 2, ASSOC.LEFT),

    "|":   (4, 2, ASSOC.LEFT),
    "^":   (5, 2, ASSOC.LEFT),
    "&":   (6, 2, ASSOC.LEFT),

    "==":  (7, 2, ASSOC.LEFT),
    "!=":  (7, 2, ASSOC.LEFT),
    "<":   (8, 2, ASSOC.LEFT),
    ">":   (8, 2, ASSOC.LEFT),
    "<=":  (8, 2, ASSOC.LEFT),
    ">=":  (8, 2, ASSOC.LEFT),

    "<<":  (9, 2, ASSOC.LEFT),
    ">>":  (9, 2, ASSOC.LEFT),

    "+":   (10, 2, ASSOC.LEFT),
    "-":   (10, 2, ASSOC.LEFT),

    "*":   (11, 2, ASSOC.LEFT),
    "/":   (11, 2, ASSOC.LEFT),
    "%":   (11, 2, ASSOC.LEFT),

    "NEG": (12, 1, ASSOC.RIGHT),
    "POS": (12, 1, ASSOC.RIGHT),
    "!":   (12, 1, ASSOC.RIGHT),
    "~":   (12, 1, ASSOC.RIGHT),

    "**":  (13, 2, ASSOC.RIGHT)
}



