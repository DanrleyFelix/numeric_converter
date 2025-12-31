import pytest # type: ignore
from src.models.command_window.evaluator.apply_operator import apply_operator
from src.models.command_window.evaluator.errors import DivisionByZeroError

@pytest.mark.parametrize("op,a,b,expected", [
    ("+", 1, 2, 3),
    ("-", 5, 3, 2),
    ("*", 4, 2, 8),
    ("/", 4, 2, 2),
    ("/", 5, 2, 2.5),
    ("%", 7, 3, 1),
    ("**", 2, 3, 8)])
def test_basic_binary_arithmetic(op, a, b, expected):
    assert apply_operator(op, a, b) == expected

@pytest.mark.parametrize("op,a,b,expected", [
    ("<<", 2.5, 1.2, 4),
    (">>", 9.9, 1.1, 4),
    ("&", 9.9, 2.2, 0),
    ("|", 8.1, 1.9, 9),
    ("^", 3.5, 1.1, 2)])
def test_bitwise_casts_to_int(op, a, b, expected):
    assert apply_operator(op, a, b) == expected

def test_division_by_zero():
    with pytest.raises(DivisionByZeroError):
        apply_operator("/", 1, 0)

