import pytest # type: ignore
from pathlib import Path
from src.models.converter.repository import PreferencesManager, DEFAULT_CONTEXT
from src.models.converter.formatter import OutputFormatter

ROOT_PATH = Path("root") 


@pytest.fixture
def prefs_manager():
    prefs = PreferencesManager(ROOT_PATH)
    prefs.set_preference("default", True)
    return prefs


@pytest.fixture
def formatter(prefs_manager):
    return OutputFormatter(prefs_manager)

def test_decimal_group_size_3_no_padding(formatter):
    context = {"group_size": 3, "zero_pad": False}
    assert formatter.format("decimal", 1222333, context) == "1 222 333"
    assert formatter.format("decimal", 22321210, context) == "22 321 210"
    assert formatter.format("decimal", 333221212, context) == "333 221 212"

def test_decimal_group_size_4_zero_pad_false_small_number(formatter):
    context = {"group_size": 4, "zero_pad": False}
    assert formatter.format("decimal", 7, context) == "7"
    assert formatter.format("decimal", 123, context) == "123"
    assert formatter.format("decimal", 1232, context) == "1232"
    assert formatter.format("decimal", 12322, context) == "1 2322"

def test_decimal_group_size_4_zero_pad_true_small_number(formatter):
    context = {"group_size": 4, "zero_pad": True}
    assert formatter.format("decimal", 7, context) == "0007"
    assert formatter.format("decimal", 123, context) == "0123"

def test_binary_group_size_4_zero_pad_true(formatter):
    context = {"group_size": 4, "zero_pad": True}
    assert formatter.format("binary", "11011001", context) == "1101 1001"
    assert formatter.format("binary", "1011", context) == "1011"
    assert formatter.format("binary", "101", context) == "0101" 
def test_binary_group_size_4_zero_pad_false(formatter):
    context = {"group_size": 4, "zero_pad": False}
    assert formatter.format("binary", "11011001", context) == "1101 1001"
    assert formatter.format("binary", "101", context) == "101"

def test_binary_group_size_1_zero_pad_true(formatter):
    context = {"group_size": 1, "zero_pad": True}
    assert formatter.format("binary", "11011", context) == "1 1 0 1 1"

def test_binary_group_size_0(formatter):
    context = {"group_size": 0, "zero_pad": True}
    assert formatter.format("binary", "110110", context) == "110110"  # sem espaços, sem padding

def test_hexBE_default(formatter):
    data = bytes([0x0E, 0x00, 0xFF])
    context = DEFAULT_CONTEXT["hexBE"]
    assert formatter.format("hexBE", data, context) == "0E 00 FF"

def test_hexLE_custom(formatter):
    data = bytes([0x0E, 0x01])
    context = {"group_size": 2, "zero_pad": True}
    assert formatter.format("hexLE", data, context) == "0E 01"

def test_hexBE_group_size_4_zero_pad(formatter):
    data = bytes([0x0E])
    context = {"group_size": 4, "zero_pad": True}
    assert formatter.format("hexBE", data, context) == "000E"
