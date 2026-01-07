import pytest # type: ignore
from src.core.command_window.evaluator.apply_operator import apply_operator
from src.core.command_window.evaluator.errors import EvaluationError, DivisionByZeroError

def test_unary_operators():
    assert apply_operator("!", 0) == 1
    assert apply_operator("NEG", 1) == -1
    assert apply_operator("POS", 3) == 3
    assert apply_operator("!", 5) == 0
    assert apply_operator("~", 2) == ~2
    assert apply_operator("~", -3) == ~-3


def test_binary_arithmetic():
    assert apply_operator("+", 2, 3) == 5
    assert apply_operator("-", 5, 3) == 2
    assert apply_operator("*", 4, 3) == 12
    assert apply_operator("/", 6, 3) == 2
    assert apply_operator("/", 5, 2) == 2.5
    assert apply_operator("%", 5, 3) == 2
    assert apply_operator("**", 2, 3) == 8

def test_comparison_operators():
    assert apply_operator("==", 5, 5) == 1
    assert apply_operator("!=", 5, 3) == 1
    assert apply_operator("<", 2, 3) == 1
    assert apply_operator("<=", 3, 3) == 1
    assert apply_operator(">", 5, 2) == 1
    assert apply_operator(">=", 5, 5) == 1

def test_bitwise_operators():
    assert apply_operator("&", 6, 3) == 2
    assert apply_operator("|", 6, 3) == 7
    assert apply_operator("^", 6, 3) == 5
    assert apply_operator("~", 2) == ~2
    assert apply_operator("<<", 1, 3) == 8
    assert apply_operator(">>", 8, 3) == 1

def test_logical_operators():
    assert apply_operator("&&", 1, 0) == 0
    assert apply_operator("&&", 1, 1) == 1
    assert apply_operator("||", 0, 0) == 0
    assert apply_operator("||", 0, 1) == 1

def test_assignment_operator():
    assert apply_operator("=", 5, 10) == 10

def test_division_by_zero():
    with pytest.raises(DivisionByZeroError):
        apply_operator("/", 5, 0)
    with pytest.raises(DivisionByZeroError):
        apply_operator("%", 5, 0)

def test_unknown_operator():
    with pytest.raises(EvaluationError):
        apply_operator("@", 1, 2)
