import pytest # type: ignore

from src.core.command_window.validator.validator import ExpressionValidator, ValidationState
from src.core.command_window.validator.errors import InvalidOperatorSequenceError
from src.core.command_window.context import cmd_window_context


@pytest.fixture(autouse=True)
def clean_context():
    ctx = cmd_window_context
    ctx.clear_all()
    ctx.set_variable("a", 2)
    ctx.set_variable("b", 4)
    ctx.set_variable("x", 3)
    ctx.set_variable("y", 3)


@pytest.mark.parametrize("text", ["1+2", "3-4", "5*6", "8/2", "7%3", "a+b", "x*2"])
def test_basic_binary_operators(text):
    state = ExpressionValidator.validate(text)
    assert state is ValidationState.ACCEPTABLE


@pytest.mark.parametrize("text", ["!1", "~2", "!a"])
def test_unary_operators(text):
    state = ExpressionValidator.validate(text)
    assert state is ValidationState.ACCEPTABLE

@pytest.mark.parametrize("text", ["2*-2","a==!b","x&&~y","5**-2","!(a==b)","~x+1"])
def test_valid_unary_operator_sequences(text):
    ExpressionValidator.validate(text)

@pytest.mark.parametrize("text", [
    "1*/2","3+*4","5-%2","6/**2","7**%2",
    "a==!=b","x<>=y","n<=*m","p>==q",
    "a&|b","x^&y","m<<>>n","p>><<q",
    "a&&||b","x||&&y",
    "a=*=b","x=||y"])
def test_invalid_operator_sequences(text):
    with pytest.raises(InvalidOperatorSequenceError):
        ExpressionValidator.validate(text)

@pytest.mark.parametrize("text", ["1+", "a*", "b&&", "x||", "(", "((", "-", "((a)"])
def test_operator_at_end_is_partial(text):
    state = ExpressionValidator.validate(text)
    assert state is ValidationState.POTENTIALLY_INVALID


@pytest.mark.parametrize("text", ["+1+2", "-3*4", "(-5)+6"])
def test_signed_numbers_in_expressions(text):
    state = ExpressionValidator.validate(text)
    assert state is ValidationState.ACCEPTABLE
