import pytest # type: ignore
from src.models.converter.converter import Converter


class TestConverter:

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
    def test_general_conversion(self, input_type, input_value, expected_decimal):
        result = Converter.convert(input_type, input_value)
        assert result["decimal"] == expected_decimal
        assert Converter.from_binary(result["binary"]) == expected_decimal
        assert int.from_bytes(result["hexBE"], byteorder="big") == expected_decimal
        assert int.from_bytes(result["hexLE"], byteorder="little") == expected_decimal
    @pytest.mark.parametrize(
        "byte_length",
        [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096])
    def test_large_byte_conversion(self, byte_length):
        max_value = (1 << (byte_length * 8)) - 1
        hex_be_bytes = Converter.to_hex_be(max_value, byte_length)
        hex_le_bytes = Converter.to_hex_le(max_value, byte_length)
        assert int.from_bytes(hex_be_bytes, byteorder="big") == max_value
        assert int.from_bytes(hex_le_bytes, byteorder="little") == max_value
        bin_str = Converter.to_binary(max_value)
        assert Converter.from_binary(bin_str) == max_value
