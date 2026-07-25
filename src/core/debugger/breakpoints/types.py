"""Validation and UI formatting for debugger breakpoint types."""

import re

ADDRESS_BREAKPOINT_TYPES = ("write", "read", "execution")
REGISTER_BREAKPOINT_TYPE = "register"
DEFAULT_BREAKPOINT_TYPE = "execution"
ADDRESS_BREAKPOINT_TYPE_CHOICES = (
    "exec",
    "w",
    "r",
    "w | r",
    "w | exec",
    "r | exec",
    "w | r | exec",
    "reg",
)
TYPE_ALIASES = {
    "exec": DEFAULT_BREAKPOINT_TYPE,
    "reg": REGISTER_BREAKPOINT_TYPE,
    "w": "write",
    "r": "read",
}
TYPE_SEPARATOR = re.compile(r"\s*(?:\|+|\bor\b)\s*", re.IGNORECASE)
HEX_ADDRESS = re.compile(r"(?:0[xX])?[0-9A-Fa-f]+")


def normalize_breakpoint_type(expression: str) -> str:
    """Return one canonical type expression or reject invalid combinations."""

    values = tuple(
        TYPE_ALIASES.get(value.casefold(), value.casefold())
        for value in TYPE_SEPARATOR.split(str(expression).strip())
    )
    if not values or any(not value for value in values):
        raise ValueError("Breakpoint type expression is invalid.")
    if len(values) != len(set(values)):
        raise ValueError("Breakpoint type expression is invalid.")
    if REGISTER_BREAKPOINT_TYPE in values:
        if values != (REGISTER_BREAKPOINT_TYPE,):
            raise ValueError("Register breakpoints cannot be combined.")
        return REGISTER_BREAKPOINT_TYPE
    if any(value not in ADDRESS_BREAKPOINT_TYPES for value in values):
        raise ValueError("Unsupported breakpoint type.")
    ordered = tuple(value for value in ADDRESS_BREAKPOINT_TYPES if value in values)
    return " || ".join(ordered)


def breakpoint_type_tokens(expression: str) -> frozenset[str]:
    """Return the validated individual types contained in an expression."""

    return frozenset(
        value.strip()
        for value in normalize_breakpoint_type(expression).split("||")
    )


def breakpoint_type_display(expression: str) -> str:
    """Return the compact Type-column representation."""

    values = normalize_breakpoint_type(expression).split(" || ")
    aliases = {
        DEFAULT_BREAKPOINT_TYPE: "exec",
        REGISTER_BREAKPOINT_TYPE: "reg",
        "write": "w",
        "read": "r",
    }
    return " | ".join(aliases.get(value, value) for value in values)


def parse_breakpoint_address(expression: str) -> int:
    """Parse a hexadecimal WHERE value and report its failing column."""

    source = str(expression).strip()
    if HEX_ADDRESS.fullmatch(source):
        return int(source, 16)
    digits = source[2:] if source.lower().startswith("0x") else source
    prefix_length = 2 if source.lower().startswith("0x") else 0
    invalid = next(
        (
            index
            for index, character in enumerate(digits)
            if character not in "0123456789abcdefABCDEF"
        ),
        len(digits),
    )
    column = prefix_length + invalid + 1
    raise ValueError(f"expected a hexadecimal address at column {column}.")
