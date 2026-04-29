import pytest  # type: ignore

from src.core.command_window.context import cmd_window_context
from src.core.command_window.validator.errors import (
    InvalidOperatorSequenceError,
    UnknownVariableError,
)
from src.core.command_window.validator.validator import ExpressionValidator, ValidationState


@pytest.fixture(autouse=True)
def clean_context():
    ctx = cmd_window_context
    ctx.clear_all()
    ctx.set_variable("A", 1)
    ctx.set_variable("B", 0)
    ctx.set_variable("value", 7)


@pytest.mark.parametrize("text", [
    "AND=1",
    "OR=1",
    "NOT=1",
    "AND_value=1",
    "ORBIT=1",
    "XOFFSET=1",
    "NOT1=1",
    "(A AND B)OR(B XOR 1)",
    "NOT(1)",
    "A AND B",
    "(A)AND(B)",
    "NOT value",
    "NOT(1)",
])
def test_textual_operator_rules_accept_valid_forms(text):
    state = ExpressionValidator.validate(text)
    assert state == ValidationState.ACCEPTABLE


@pytest.mark.parametrize("text", [
    "A AND",
    "(A)OR",
    "NOT",
    "A AND NOT",
    "20 OR",
    "20 AN",
])
def test_textual_operator_rules_detect_partial_forms(text):
    state = ExpressionValidator.validate(text)
    assert state == ValidationState.POTENTIALLY_INVALID


@pytest.mark.parametrize("text", [
    "(NOT)1",
    "A(OR)B",
])
def test_textual_operator_rules_reject_invalid_parenthesized_forms(text):
    with pytest.raises(InvalidOperatorSequenceError):
        ExpressionValidator.validate(text)


@pytest.mark.parametrize("text", [
    "AORB",
    "ORbit",
    "NOTvalue",
    "XORvalue",
])
def test_textual_operator_rules_do_not_treat_undelimited_words_as_operators(text):
    with pytest.raises(UnknownVariableError):
        ExpressionValidator.validate(text)


def test_textual_operator_rules_report_unknown_variable_in_complete_expression():
    with pytest.raises(UnknownVariableError, match='Unknown variable "C"\\.'):
        ExpressionValidator.validate("(C AND B)OR(B XOR 1)")
