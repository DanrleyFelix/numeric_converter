import pytest # type: ignore
from src.models.command_window.validator.validator import ExpressionValidator, ValidationState
from src.models.command_window.context import Context
from src.models.command_window.validator.errors import (
    InvalidStartError, InvalidOperatorSequenceError,
    ParenthesisMismatchError, UnknownTokenError, UnknownVariableError
)


def test_unary_and_binary_operators():
    ctx = Context()
    ctx.set_variable("x", 5)
    ctx.set_variable("y", 2)

    print("\nTest: múltiplos operadores unários")
    with pytest.raises(InvalidOperatorSequenceError):
        ExpressionValidator.validate("--x", ctx)

    with pytest.raises(InvalidOperatorSequenceError):
        ExpressionValidator.validate("+sqrt(4)", ctx)

    with pytest.raises(InvalidOperatorSequenceError):
        ExpressionValidator.validate("~~x", ctx)

    print("\nTest: operador binário seguido de unário")
    result = ExpressionValidator.validate("x + -y", ctx)
    print("x + -y ->", result)
    assert result == ValidationState.ACCEPTABLE

    print("\nTest: sequência inválida de binários")
    with pytest.raises(InvalidOperatorSequenceError):
        ExpressionValidator.validate("x + * 3", ctx)


def test_numbers_different_bases():
    ctx = Context()
    print("\nTest: números decimais, binários e hexadecimais")
    expr = "123 + 0b101 - 0x1A"
    result = ExpressionValidator.validate(expr, ctx)
    print(expr, "->", result)
    assert result == ValidationState.ACCEPTABLE

    print("\nTest: número inválido de base")
    with pytest.raises(UnknownTokenError):
        ExpressionValidator.validate("0b102", ctx)


def test_variables_and_assignments():
    ctx = Context()
    ctx.set_variable("a", 10)
    ctx.set_variable("b", 5)

    print("\nTest: variável desconhecida")
    with pytest.raises(UnknownVariableError):
        ExpressionValidator.validate("c + 2", ctx)

    print("\nTest: múltiplas atribuições")
    with pytest.raises(InvalidOperatorSequenceError):
        ExpressionValidator.validate("x = y = a + b", ctx)

    print("\nTest: lhs é operador unário (inválido)")
    with pytest.raises(InvalidStartError):
        ExpressionValidator.validate("-x = 5", ctx)


def test_complex_parentheses():
    ctx = Context()
    ctx.set_variable("x", 3)
    ctx.set_variable("y", 4)

    print("\nTest: parênteses aninhados")
    expr = "((x + 2) * (y - 1))"
    result = ExpressionValidator.validate(expr, ctx)
    print(expr, "->", result)
    assert result == ValidationState.ACCEPTABLE

    print("\nTest: parêntese vazio dentro de expressão")
    with pytest.raises(ParenthesisMismatchError):
        ExpressionValidator.validate("(x + ())", ctx)

    print("\nTest: parêntese parcialmente fechado")
    expr = "(x + (y - 2)"
    result = ExpressionValidator.validate(expr, ctx)
    print(expr, "->", result)
    assert result == ValidationState.POTENTIALLY_INVALID


def test_spaces_and_illegal_characters():
    ctx = Context()
    ctx.set_variable("x", 1)

    print("\nTest: espaços e tabs")
    expr = "  x  +  2\t-  3 "
    result = ExpressionValidator.validate(expr, ctx)
    print(f"'{expr}' ->", result)
    assert result == ValidationState.ACCEPTABLE

    print("\nTest: caractere ilegal")
    with pytest.raises(UnknownTokenError):
        ExpressionValidator.validate("x + $", ctx)


def test_edge_cases():
    ctx = Context()
    ctx.set_variable("x", 2)

    print("\nTest: apenas parênteses")
    with pytest.raises(ParenthesisMismatchError):
        ExpressionValidator.validate("()", ctx)

    print("\nTest: apenas operador unário")
    result = ExpressionValidator.validate("-", ctx)
    print("- ->", result)
    assert result == ValidationState.POTENTIALLY_INVALID

    print("\nTest: variável desconhecida sozinha")
    with pytest.raises(UnknownVariableError):
        ExpressionValidator.validate("y", ctx)
