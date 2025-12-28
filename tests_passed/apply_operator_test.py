import pytest # type: ignore
from src.models.command_window.evaluator.errors import (
    EvaluationError,
    DivisionByZeroError,
    InvalidUnaryOperationError)
from src.models.command_window.evaluator.evaluator import apply_operator


def test_unary_operators():
    assert apply_operator("!", 0) == 1
    assert apply_operator("!", 5) == 0
    assert apply_operator("~", 2) == ~2
    assert apply_operator("sqrt", 9) == 3
    assert apply_operator("sqrt", 2) == pytest.approx(1.4142, 0.0001)
    with pytest.raises(InvalidUnaryOperationError):
        apply_operator("sqrt", -4)
    with pytest.raises(EvaluationError):
        apply_operator("+", 5)


def test_arithmetic_operators():
    assert apply_operator("+", 3, 2) == 5
    assert apply_operator("-", 3, 2) == 1
    assert apply_operator("*", 3, 2) == 6
    assert apply_operator("/", 4, 2) == 2
    assert apply_operator("/", 5, 2) == 2.5
    with pytest.raises(DivisionByZeroError):
        apply_operator("/", 5, 0)
    assert apply_operator("%", 5, 2) == 1
    with pytest.raises(DivisionByZeroError):
        apply_operator("%", 5, 0)
    assert apply_operator("**", 2, 3) == 8


def test_comparison_operators():
    assert apply_operator("==", 2, 2) == 1
    assert apply_operator("==", 2, 3) == 0
    assert apply_operator("!=", 2, 3) == 1
    assert apply_operator("<", 2, 3) == 1
    assert apply_operator("<=", 2, 2) == 1
    assert apply_operator(">", 3, 2) == 1
    assert apply_operator(">=", 3, 3) == 1


def test_bitwise_operators():
    assert apply_operator("<<", 2, 3) == 16
    assert apply_operator(">>", 16, 2) == 4
    assert apply_operator("&", 6, 3) == 2
    assert apply_operator("|", 6, 3) == 7
    assert apply_operator("^", 6, 3) == 5


def test_logical_operators():
    assert apply_operator("&&", 1, 0) == 0
    assert apply_operator("&&", 1, 2) == 1
    assert apply_operator("||", 0, 0) == 0
    assert apply_operator("||", 0, 2) == 1


def test_assignment_operator():
    assert apply_operator("=", 10, 5) == 5


def test_unknown_operator():
    with pytest.raises(EvaluationError):
        apply_operator("???", 1, 2)
