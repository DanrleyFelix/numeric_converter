import pytest # type: ignore
from src.models.command_window.validator.validator import ExpressionValidator, ValidationState
from src.models.command_window.context import Context
from src.models.command_window.validator.errors import (
    InvalidStartError, UnknownTokenError, UnknownVariableError, ParenthesisMismatchError, InvalidOperatorSequenceError)


def test_validator_empty_and_invalid_start():
    ctx = Context()

    result = ExpressionValidator.validate("", ctx)
    assert result == ValidationState.POTENTIALLY_INVALID

    with pytest.raises(InvalidStartError):
        ExpressionValidator.validate("* 2 + 3", ctx)

    with pytest.raises(UnknownTokenError):
        ExpressionValidator.validate("@@@", ctx)

def test_validator_parentheses_and_operator_sequence():
    ctx = Context()
    ctx.set_variable("x", 10)

    with pytest.raises(ParenthesisMismatchError):
        ExpressionValidator.validate("(x + 2))", ctx)

    with pytest.raises(ParenthesisMismatchError):
        ExpressionValidator.validate("(()", ctx)

    with pytest.raises(InvalidOperatorSequenceError):
        ExpressionValidator.validate("x + * 3", ctx)

    with pytest.raises(ParenthesisMismatchError):
        ExpressionValidator.validate("( )", ctx)

    with pytest.raises(InvalidOperatorSequenceError):
        ExpressionValidator.validate("2(3 + x)", ctx)

def test_validator_variables_and_partial_state():
    ctx = Context()
    ctx.set_variable("x", 5)

    with pytest.raises(UnknownVariableError):
        ExpressionValidator.validate("y + 2", ctx)

    result = ExpressionValidator.validate("x + ", ctx)
    assert result == ValidationState.POTENTIALLY_INVALID

    result = ExpressionValidator.validate("(x + 2", ctx)
    assert result == ValidationState.POTENTIALLY_INVALID

    result = ExpressionValidator.validate("x + 3", ctx)
    assert result == ValidationState.ACCEPTABLE

    result = ExpressionValidator.validate("(x + 3) * 2", ctx)
    assert result == ValidationState.ACCEPTABLE

def test_validator_tokenization_and_empty_expression():
    ctx = Context()
    
    print("\nTest: expressão vazia")
    result = ExpressionValidator.validate("", ctx)
    print("Resultado:", result)
    assert result == ValidationState.POTENTIALLY_INVALID

    print("\nTest: token desconhecido")
    with pytest.raises(UnknownTokenError):
        ExpressionValidator.validate("@@@", ctx)


def test_validator_start():
    ctx = Context()
    ctx.set_variable("x", 10)

    print("\nTest: operador binário no início")
    with pytest.raises(InvalidStartError):
        ExpressionValidator.validate("* x + 2", ctx)

    print("\nTest: operador unário no início (-)")
    result = ExpressionValidator.validate("-x + 2", ctx)
    print("Resultado:", result)
    assert result == ValidationState.ACCEPTABLE

    print("\nTest: número no início")
    result = ExpressionValidator.validate("3 + x", ctx)
    print("Resultado:", result)
    assert result == ValidationState.ACCEPTABLE


def test_validator_parentheses_and_operator_sequences():
    ctx = Context()
    ctx.set_variable("x", 10)

    print("\nTest: parênteses desequilibrados")
    with pytest.raises(ParenthesisMismatchError):
        ExpressionValidator.validate("(x + 2))", ctx)
    with pytest.raises(ParenthesisMismatchError):
        ExpressionValidator.validate("(()", ctx)

    print("\nTest: parêntese vazio")
    with pytest.raises(ParenthesisMismatchError):
        ExpressionValidator.validate("( )", ctx)

    print("\nTest: sequência inválida de operadores")
    with pytest.raises(InvalidOperatorSequenceError):
        ExpressionValidator.validate("x + * 3", ctx)
    with pytest.raises(InvalidOperatorSequenceError):
        ExpressionValidator.validate("2(3 + x)", ctx)


def test_validator_variable_usage_and_assignment():
    ctx = Context()
    ctx.set_variable("x", 5)

    print("\nTest: variável desconhecida")
    with pytest.raises(UnknownVariableError):
        ExpressionValidator.validate("y + 2", ctx)

    print("\nTest: variável lhs de '=' não precisa existir")
    result = ExpressionValidator.validate("y = x + 2", ctx)
    print("Resultado:", result)
    assert result == ValidationState.ACCEPTABLE


def test_validator_partial_and_acceptable_expressions():
    ctx = Context()
    ctx.set_variable("x", 3)

    print("\nTest: expressão parcial termina com operador")
    result = ExpressionValidator.validate("x + ", ctx)
    print("Resultado:", result)
    assert result == ValidationState.POTENTIALLY_INVALID

    print("\nTest: expressão parcial abre parêntese sem fechar")
    result = ExpressionValidator.validate("(x + 2", ctx)
    print("Resultado:", result)
    assert result == ValidationState.POTENTIALLY_INVALID

    print("\nTest: expressão aceitável simples")
    result = ExpressionValidator.validate("x + 3", ctx)
    print("Resultado:", result)
    assert result == ValidationState.ACCEPTABLE

    print("\nTest: expressão aceitável complexa")
    result = ExpressionValidator.validate("(x + 3) * 2 - sqrt(4)", ctx)
    print("Resultado:", result)
    assert result == ValidationState.ACCEPTABLE