from src.presentation.formatters.converter_output import OutputFormatter
from src.application.dto.formatting_context import FormattingOutputDTO


def test_group_string_basic_cases():
    f = OutputFormatter()
    assert f._group_string("1234", 2) == "12 34"
    assert f._group_string("12345", 2) == "1 23 45"
    assert f._group_string("123456", 3) == "123 456"
    assert f._group_string("1234567", 3) == "1 234 567"

def test_group_string_disabled_grouping():
    f = OutputFormatter()
    assert f._group_string("123", 0) == "123"
    assert f._group_string("123", -1) == "123"

def test_format_decimal_without_zero_pad():
    f = OutputFormatter()
    cfg = FormattingOutputDTO(group_size=3, zero_pad=False)
    result = f.format_decimal(12345, cfg)
    assert result == "12 345"

def test_format_decimal_with_zero_pad_no_grouping():
    f = OutputFormatter()
    cfg = FormattingOutputDTO(group_size=4, zero_pad=True)
    result = f.format_decimal(123, cfg)
    assert result == "0123"

def test_format_decimal_with_zero_pad_and_grouping():
    f = OutputFormatter()
    cfg = FormattingOutputDTO(group_size=3, zero_pad=True)
    result = f.format_decimal(45, cfg)
    assert result == "045"

def test_format_decimal_group_size_disabled():
    f = OutputFormatter()
    cfg_zero = FormattingOutputDTO(group_size=0, zero_pad=True)
    cfg_negative = FormattingOutputDTO(group_size=-1, zero_pad=True)
    assert f.format_decimal(123, cfg_zero) == "123"
    assert f.format_decimal(123, cfg_negative) == "123"

def test_format_binary_without_zero_pad():
    f = OutputFormatter()
    cfg = FormattingOutputDTO(group_size=4, zero_pad=False)
    result = f.format_binary("101011", cfg)
    assert result == "10 1011"

def test_format_binary_with_zero_pad():
    f = OutputFormatter()
    cfg = FormattingOutputDTO(group_size=4, zero_pad=True)
    result = f.format_binary("101", cfg)
    assert result == "0101"

def test_format_binary_with_zero_pad_and_grouping():
    f = OutputFormatter()
    cfg = FormattingOutputDTO(group_size=3, zero_pad=True)
    result = f.format_binary("11", cfg)
    assert result == "011"

def test_format_binary_group_size_disabled():
    f = OutputFormatter()
    cfg_zero = FormattingOutputDTO(group_size=0, zero_pad=True)
    cfg_negative = FormattingOutputDTO(group_size=-1, zero_pad=True)
    assert f.format_binary("101", cfg_zero) == "101"
    assert f.format_binary("101", cfg_negative) == "101"

def test_format_hex_basic():
    f = OutputFormatter()
    cfg = FormattingOutputDTO(group_size=2, zero_pad=False)
    value = bytes([0xDE, 0xAD, 0xBE, 0xEF])
    result = f.format_hex(value, cfg)
    assert result == "DE AD BE EF"

def test_format_hex_with_zero_pad_group_size_4():
    f = OutputFormatter()
    cfg = FormattingOutputDTO(group_size=4, zero_pad=True)
    value = bytes([0x0A, 0xF2, 0xAA])  # "0AF2AA"
    result = f.format_hex(value, cfg)
    assert result == "000A F2AA"

def test_format_hex_with_zero_pad_and_grouping():
    f = OutputFormatter()
    cfg = FormattingOutputDTO(group_size=3, zero_pad=True)
    value = bytes([0x1])
    result = f.format_hex(value, cfg)
    assert result == "001"

def test_format_hex_group_size_disabled():
    f = OutputFormatter()
    cfg_zero = FormattingOutputDTO(group_size=0, zero_pad=True)
    cfg_negative = FormattingOutputDTO(group_size=-1, zero_pad=True)
    value = bytes([0xFF])
    assert f.format_hex(value, cfg_zero) == "FF"
    assert f.format_hex(value, cfg_negative) == "FF"

def test_formatter_is_stateless():
    f = OutputFormatter()
    cfg = FormattingOutputDTO(group_size=2, zero_pad=True)
    r1 = f.format_decimal(1, cfg)
    r2 = f.format_decimal(1, cfg)
    assert r1 == r2
