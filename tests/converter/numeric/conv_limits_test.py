import pytest  # type: ignore

from src.core.converter import Converter, ConverterValidationError, MAX_BYTE_LENGTH
from src.core.converter.validator import NumericValidator


def test_hex_requires_complete_bytes():
    with pytest.raises(ConverterValidationError):
        Converter.from_hex("ABC")


def test_binary_limit_is_enforced():
    too_long_binary = "1" * ((MAX_BYTE_LENGTH * 8) + 1)
    assert NumericValidator.validate("binary", too_long_binary) is False
    with pytest.raises(ConverterValidationError):
        Converter.from_binary(too_long_binary)


def test_decimal_limit_is_enforced():
    too_large_decimal = str(1 << (MAX_BYTE_LENGTH * 8))
    assert NumericValidator.validate("decimal", too_large_decimal) is False
    with pytest.raises(ConverterValidationError):
        Converter.convert("decimal", too_large_decimal)
