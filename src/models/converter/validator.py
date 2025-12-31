from src.models.constants import DECIMAL_DIGITS, BINARY_DIGITS, HEX_DIGITS


class NumericValidator:

    @staticmethod
    def is_decimal(value: str) -> bool:
        return all(char in DECIMAL_DIGITS for char in value)

    @staticmethod
    def is_binary(value: str) -> bool:
        return all(char in BINARY_DIGITS for char in value)

    @staticmethod
    def is_hex(value: str) -> bool:
        return all(char in HEX_DIGITS for char in value)

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
