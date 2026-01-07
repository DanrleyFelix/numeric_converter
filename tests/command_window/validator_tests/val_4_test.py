import pytest # type: ignore

from src.core.command_window.validator.validator import ExpressionValidator, ValidationState
from src.core.command_window.validator.errors import (
    InvalidOperatorSequenceError,
    ParenthesisMismatchError,
    UnknownVariableError)
from src.core.command_window.context import cmd_window_context


@pytest.fixture(autouse=True)
def clean_context():
    ctx = cmd_window_context
    ctx.clear_all()
    ctx.set_variable("a", 1)
    ctx.set_variable("b", 2)
    ctx.set_variable("c", 3)

@pytest.mark.parametrize("text", ["a+b*c-2","a*(b+c*(a-b))","!(a==b)||c>2","~a&b|c^a","a<<2+b>>1", "a <= -2", "2 <= -3", "-3==-3", "2>=-2"])
def test_complex_valid_expressions(text):
    state = ExpressionValidator.validate(text)
    assert state == ValidationState.ACCEPTABLE

@pytest.mark.parametrize("text", ["a+*b","a&&==b","a<<|b","a**==b","a=/b", "!-2", "2&-2", "a-*2", "a+*2", "a=*2", "a==*2", "a>-*2", "2>=*-4"])
def test_deep_invalid_operator_sequences(text):
    with pytest.raises(InvalidOperatorSequenceError):
        ExpressionValidator.validate(text)

@pytest.mark.parametrize("text", ["!!a","~~b","!~a","+-a"])
def test_multiple_unary_not_allowed(text):
    with pytest.raises(InvalidOperatorSequenceError):
        ExpressionValidator.validate(text)

@pytest.mark.parametrize("text", ["!a","~b","-a","+b","a*-b","a==!b"])
def test_valid_unary_usage(text):
    state = ExpressionValidator.validate(text)
    assert state == ValidationState.ACCEPTABLE

@pytest.mark.parametrize("text", ["a=b+1","c=a*(b+2)","a=!(b==2)"])
def test_assignment_with_expression(text):
    state = ExpressionValidator.validate(text)
    assert state == ValidationState.ACCEPTABLE


@pytest.mark.parametrize("text", ["a=b=1","(a)=1","a=(b)=2"])
def test_invalid_assignment_forms(text):
    with pytest.raises(InvalidOperatorSequenceError):
        ExpressionValidator.validate(text)


@pytest.mark.parametrize("text", ["a+x*2","!(b+y)","c+(z*2)"])
def test_unknown_variable_deep(text):
    with pytest.raises(UnknownVariableError):
        ExpressionValidator.validate(text)


@pytest.mark.parametrize("text", ["a+","a*(b+","!(a==","a<<"])
def test_complex_partial_states(text):
    state = ExpressionValidator.validate(text)
    assert state == ValidationState.POTENTIALLY_INVALID


@pytest.mark.parametrize("text", ["a+(b))","a+()","!(())"])
def test_advanced_parenthesis_errors(text):
    with pytest.raises(ParenthesisMismatchError):
        ExpressionValidator.validate(text)
