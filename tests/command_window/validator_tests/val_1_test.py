import pytest # type: ignore

from src.core.command_window.validator.validator import (
    ExpressionValidator,
    ValidationState,
)
from src.core.command_window.validator.errors import (
    InvalidStartError,
    ParenthesisMismatchError,
)
from src.core.command_window.context import cmd_window_context

@pytest.fixture(autouse=True)
def clean_context():
    ctx = cmd_window_context
    ctx.clear_all()
    ctx.set_variable("a", 2)
    ctx.set_variable("x", 3)
    ctx.set_variable("b", 4)
    ctx.set_variable("y", -1)


@pytest.mark.parametrize("text", [ "", " ", "   ", "\n\t"])
def test_empty_expression_is_potentially_invalid(text):
    state = ExpressionValidator.validate(text)
    assert state is ValidationState.POTENTIALLY_INVALID


@pytest.mark.parametrize("text", ["0", "1", "42", "-1", "+2", "3.14", "-0.5", "0b101", "-0xFF"])
def test_single_number_is_valid(text):
    state = ExpressionValidator.validate(text)
    assert state is ValidationState.ACCEPTABLE

@pytest.mark.parametrize("text", ["*2", "/3", "%4", "&&1", "||0", "="])
def test_invalid_start_raises(text):
    with pytest.raises(InvalidStartError):
        ExpressionValidator.validate(text)

@pytest.mark.parametrize("text", ["(1)", "((2))", "(1+2)", "(-2)", "(-2+3)", "(a)"])
def test_valid_parentheses(text):
    state = ExpressionValidator.validate(text)
    assert state is ValidationState.ACCEPTABLE

@pytest.mark.parametrize("text", [")", "1)", "(1))", "()", "(()"])
def test_invalid_parentheses(text):
    with pytest.raises(ParenthesisMismatchError):
        ExpressionValidator.validate(text)

@pytest.mark.parametrize("text", ["(", "(1+", "1+", "1*", "a="])
def test_partial_expressions_are_potentially_invalid(text):
    state = ExpressionValidator.validate(text)
    assert state is ValidationState.POTENTIALLY_INVALID
