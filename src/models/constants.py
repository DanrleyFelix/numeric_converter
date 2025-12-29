import re
from enum import Enum, auto

DECIMAL_DIGITS = "0123456789"
BINARY_DIGITS = "01"
HEX_DIGITS = "0123456789abcdefABCDEF"

OPERATORS = {"+", "-", "*", "/", "%", "**",
    "<<", ">>", "==", "!=", "<", ">", "<=", ">=",
    "&", "|", "^", "~", "&&", "||", "!", "="}
UNARY_OPERATORS = {"!", "~"}
SIGNALS = {"+", "-"}
BASE_PREFIXES = {"0b": 2, "0x": 16}

MULTI_CHAR_OPERATORS = sorted(OPERATORS, key=len, reverse=True)

ERROR_INVALID_EXPRESSION = ("Invalid expression. Use BACKSPACE or X key to delete it.")
ERROR_DIVISION_BY_ZERO = "Division by zero."
ERROR_UNKNOWN_TOKEN = "Unknown token."

IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
WHITESPACE_RE = re.compile(r"\s+")

REGEX_HEX_PAIR = re.compile(r"..")
REGEX_BINARY_GROUP = re.compile(r"....")

class Assoc(Enum):
    LEFT = auto()
    RIGHT = auto()

OPERATOR_INFO = {
    # operator : (precedence, arity, associativity)

    "=":   (1, 2, Assoc.RIGHT),

    "||":  (2, 2, Assoc.LEFT),
    "&&":  (3, 2, Assoc.LEFT),

    "|":   (4, 2, Assoc.LEFT),
    "^":   (5, 2, Assoc.LEFT),
    "&":   (6, 2, Assoc.LEFT),

    "==":  (7, 2, Assoc.LEFT),
    "!=":  (7, 2, Assoc.LEFT),
    "<":   (8, 2, Assoc.LEFT),
    ">":   (8, 2, Assoc.LEFT),
    "<=":  (8, 2, Assoc.LEFT),
    ">=":  (8, 2, Assoc.LEFT),

    "<<":  (9, 2, Assoc.LEFT),
    ">>":  (9, 2, Assoc.LEFT),

    "+":   (10, 2, Assoc.LEFT),
    "-":   (10, 2, Assoc.LEFT),
    "*":   (11, 2, Assoc.LEFT),
    "/":   (11, 2, Assoc.LEFT),
    "%":   (11, 2, Assoc.LEFT),

    "**":  (12, 2, Assoc.RIGHT),

    "!":   (13, 1, Assoc.RIGHT),
    "~":   (13, 1, Assoc.RIGHT),
    "sqrt":(13, 1, Assoc.RIGHT),
}

