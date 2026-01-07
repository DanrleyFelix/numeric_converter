import pytest # type: ignore
from src.core.converter.converter import Converter


@pytest.mark.parametrize(
    "input_type,input_value,expected_decimal",
    [
        ("decimal", "10", 10),
        ("binary", "1010", 10),
        ("hexBE", "00 0A", 10),
        ("hexLE", "0A 00", 10),
        ("decimal", "255", 255),
        ("binary", "11111111", 255),
        ("hexBE", "00 FF", 255),
        ("hexLE", "FF 00", 255),
        ("decimal", "65535", 65535),
        ("binary", "1111111111111111", 65535),
        ("hexBE", "FF FF", 65535),
        ("hexLE", "FF FF", 65535),
    ])
def test_general_conversion(input_type, input_value, expected_decimal):
    result = Converter.convert(input_type, input_value)
    assert result["decimal"] == expected_decimal
    assert Converter.from_binary(result["binary"]) == expected_decimal
    assert int.from_bytes(result["hexBE"], byteorder="big") == expected_decimal
    assert int.from_bytes(result["hexLE"], byteorder="little") == expected_decimal
