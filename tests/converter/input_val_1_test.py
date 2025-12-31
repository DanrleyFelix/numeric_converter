import pytest # type: ignore
from src.models.converter.validator import NumericValidator


class TestNumericValidator:

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("123", True),
            ("0", True),
            ("00123", True),
            ("", True),    
            ("12a3", False)])
    def test_decimal_validation(self, value, expected):
        assert NumericValidator.validate("decimal", value) == expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("1010", True),
            ("0", True),
            ("1", True),
            ("000101", True),   
            ("10201", False),
            ("100F", False),
            ("@10001", False)])
    def test_binary_validation(self, value, expected):
        assert NumericValidator.validate("binary", value) == expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("0F", True),
            ("aB12", True),
            ("00FF", True), 
            ("G1", False)])
    def test_hex_be_validation(self, value, expected):
        assert NumericValidator.validate("hexBE", value) == expected

    @pytest.mark.parametrize(
        "value,expected", [
            ("0F", True),
            ("aB12", True),
            ("00FF", True),
            ("G1", False),
            ("@AF", False),
            ("0xA@F", False),
            ("A@F", False),
            ("0xAF", False)])
    def test_hex_le_validation(self, value, expected):
        assert NumericValidator.validate("hexLE", value) == expected
