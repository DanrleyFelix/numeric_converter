import pytest  # type: ignore

from src.core.command_window.validator.errors import InvalidStartError
from src.core.command_window.validator.validator import ExpressionValidator
from src.presentation.presenter.command_window.editing import trim_invalid_suffix


def test_trim_invalid_suffix_keeps_rhs_when_left_side_is_being_corrected():
    corrected = trim_invalid_suffix("* 20", ExpressionValidator.validate)

    assert corrected == "* 20"


def test_trim_invalid_suffix_keeps_hex_prefix_when_previous_number_is_being_corrected():
    corrected = trim_invalid_suffix("0x * 2423 + 34", ExpressionValidator.validate)

    assert corrected == "0x * 2423 + 34"


@pytest.mark.parametrize("text", ["*", "* "])
def test_trim_invalid_suffix_still_removes_incomplete_operator_start(text):
    corrected = trim_invalid_suffix(text, ExpressionValidator.validate)

    assert corrected == ""


def test_trim_invalid_suffix_still_removes_invalid_typing_suffix():
    corrected = trim_invalid_suffix("200 **", ExpressionValidator.validate)

    assert corrected == "200 *"


def test_preserved_rhs_still_validates_as_invalid_start():
    with pytest.raises(InvalidStartError):
        ExpressionValidator.validate("* 20")
