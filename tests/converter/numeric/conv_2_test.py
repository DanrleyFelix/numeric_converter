import pytest # type: ignore
from src.models.converter.converter import Converter

def test_large_byte_conversion():
    for byte_length in [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]:
        max_value = (1 << (byte_length * 8)) - 1
        hex_be_bytes = Converter.to_hex_be(max_value, byte_length)
        hex_le_bytes = Converter.to_hex_le(max_value, byte_length)
        dec_from_be = int.from_bytes(hex_be_bytes, byteorder="big")
        dec_from_le = int.from_bytes(hex_le_bytes, byteorder="little")
        assert dec_from_be == max_value, f"Falhou para BE com {byte_length} bytes"
        assert dec_from_le == max_value, f"Falhou para LE com {byte_length} bytes"
        bin_str = Converter.to_binary(max_value)
        dec_from_bin = Converter.from_binary(bin_str)
        assert dec_from_bin == max_value, f"Falhou para binário com {byte_length} bytes"
