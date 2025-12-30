import pytest # type: ignore

from src.models.command_window.validator.validator import ExpressionValidator, ValidationState
from src.models.command_window.validator.errors import (
    InvalidStartError,
    InvalidOperatorSequenceError,
    ParenthesisMismatchError,
    UnknownVariableError)
from src.models.command_window.context import Context


def ctx():
    c = Context()
    c.set_variable("a", 1)
    c.set_variable("b", 2)
    return c


@pytest.mark.parametrize("text", [
    "*1","/2","==3","&&a","||b","=1"])
def test_invalid_start(text):
    with pytest.raises(InvalidStartError):
        ExpressionValidator.validate(text, ctx())

@pytest.mark.parametrize("text", ["1=2","a=b=3","(a)=2"])
def test_invalid_assignment(text):
    with pytest.raises(InvalidOperatorSequenceError):
        ExpressionValidator.validate(text, ctx())

@pytest.mark.parametrize("text", ["x+1","a+y"])
def test_unknown_variable(text):
    with pytest.raises(UnknownVariableError):
        ExpressionValidator.validate(text, ctx())

@pytest.mark.parametrize("text", ["(", "(1+2", "a*(b+1"])
def test_partial_parentheses_state(text):
    state = ExpressionValidator.validate(text, ctx())
    assert state == ValidationState.POTENTIALLY_INVALID

@pytest.mark.parametrize("text", ["1+","a*","b==","a&&"])
def test_partial_operator_state(text):
    state = ExpressionValidator.validate(text, ctx())
    assert state == ValidationState.POTENTIALLY_INVALID

@pytest.mark.parametrize("text", ["1+2", "a+b*2", "(a+b)*2", "a=1", "b=a+3", "!(a==b)"])
def test_valid_complete_expressions(text):
    state = ExpressionValidator.validate(text, ctx())
    assert state == ValidationState.ACCEPTABLE




