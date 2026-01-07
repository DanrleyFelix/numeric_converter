import pytest # type: ignore

from src.core.command_window.validator.validator import ExpressionValidator, ValidationState
from src.core.command_window.validator.errors import (
    InvalidStartError,
    InvalidOperatorSequenceError,
    UnknownVariableError)
from src.core.command_window.context import cmd_window_context

@pytest.fixture(autouse=True)
def clean_context():
    ctx = cmd_window_context
    ctx.clear_all()
    ctx.set_variable("a", 1)
    ctx.set_variable("b", 2)


@pytest.mark.parametrize("text", [
    "*1","/2","==3","&&a","||b","=1"])
def test_invalid_start(text):
    with pytest.raises(InvalidStartError):
        ExpressionValidator.validate(text)

@pytest.mark.parametrize("text", ["1=2","a=b=3","(a)=2"])
def test_invalid_assignment(text):
    with pytest.raises(InvalidOperatorSequenceError):
        ExpressionValidator.validate(text)

@pytest.mark.parametrize("text", ["x+1","a+y"])
def test_unknown_variable(text):
    with pytest.raises(UnknownVariableError):
        ExpressionValidator.validate(text)

@pytest.mark.parametrize("text", ["(", "(1+2", "a*(b+1"])
def test_partial_parentheses_state(text):
    state = ExpressionValidator.validate(text)
    assert state == ValidationState.POTENTIALLY_INVALID

@pytest.mark.parametrize("text", ["1+","a*","b==","a&&"])
def test_partial_operator_state(text):
    state = ExpressionValidator.validate(text)
    assert state == ValidationState.POTENTIALLY_INVALID

@pytest.mark.parametrize("text", ["1+2", "a+b*2", "(a+b)*2", "a=1", "b=a+3", "!(a==b)"])
def test_valid_complete_expressions(text):
    state = ExpressionValidator.validate(text)
    assert state == ValidationState.ACCEPTABLE

@pytest.mark.parametrize(
    "expr", [
        "a + b = 3",
        "2 = a",       
        "(a) = 3",   
        "a * b = c"])
def test_invalid_assignment_lhs(expr):
    ctx = cmd_window_context
    ctx.set_variable("a", 1)
    ctx.set_variable("b", 2)
    ctx.set_variable("c", 3)

    with pytest.raises(InvalidOperatorSequenceError):
        ExpressionValidator.validate(expr)
