import pytest # type: ignore
from src.core.command_window.validator.validator import ExpressionValidator, ValidationState
from src.core.command_window.context import cmd_window_context


@pytest.fixture(autouse=True)
def clean_context():
    ctx = cmd_window_context
    ctx.clear_all()

@pytest.mark.parametrize("text, should_pass", [
    ("value = 1", True),
    ("_value = 2", True),
    ("Value = 3", True),
    ("_Value = 4", True),
    ("VALUE = 0x2ABCDEF - 0b1011", True),
    ("value_1 = 25", True),
    ("value1 = 43", True),

    ("myVar = 5 + 3 * (2 - 1)", True),
    ("_x = 0b1010 & 0xFF", True),
    ("TOTAL = 123 / 3.0", True),
    ("score_value = (10**2) % 7", True),
    ("delta_ = ((5 + 2) << 1) - 3", True),
    ("a_b_c = 1 || 0 && 1", True),

    ("1value = 2", False),
    ("1_value = 3", False),

    ("@ = 1", False),
    ("@_value = 3", False),
    ("#@!value = 1", False),

    ("value_$ = 3", False),
    ("val@ue = 2", False),
    ("v@_name = 5", False),

    ("$value = 3", False),
    ("%var = 1", False),
    ("!var = 2", False),
    ("value# = 10", False),

    (" value\t=\t42 ", True),
    ("\t_value = 0b1010\n", True),
    ("Value = 3 + 4 * (2 - 1)  ", True),
    ("1value\t= 2", False),
    ("@value = 10", False)])
def test_assignment_validation_general(text, should_pass):
    if should_pass:
        state = ExpressionValidator.validate(text)
        assert state == ValidationState.ACCEPTABLE
    else:
        with pytest.raises(Exception):
            ExpressionValidator.validate(text)
