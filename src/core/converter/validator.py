import sys

from src.core.converter.errors import MAX_BYTE_LENGTH
from src.core.constants import DECIMAL_DIGITS, BINARY_DIGITS, HEX_DIGITS

if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)


class NumericValidator:

    @staticmethod
    def is_decimal(value: str) -> bool:
        if not all(char in DECIMAL_DIGITS for char in value):
            return False
        if not value:
            return True
        return max(1, (int(value).bit_length() + 7) // 8) <= MAX_BYTE_LENGTH

    @staticmethod
    def is_binary(value: str) -> bool:
        if not all(char in BINARY_DIGITS for char in value):
            return False
        return len(value) <= (MAX_BYTE_LENGTH * 8)

    @staticmethod
    def is_hex(value: str) -> bool:
        if not all(char in HEX_DIGITS for char in value):
            return False
        return len(value) % 2 == 0 and (len(value) // 2) <= MAX_BYTE_LENGTH

    @staticmethod
    def validate(input_type: str, value: str) -> bool:
        if input_type == "decimal":
            return NumericValidator.is_decimal(value)
        elif input_type == "binary":
            return NumericValidator.is_binary(value)
        elif input_type in ("hexBE", "hexLE"):
            return NumericValidator.is_hex(value)
        else:
            return False
