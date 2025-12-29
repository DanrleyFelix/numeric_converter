import pytest # type: ignore

from src.models.command_window.tokenizer.tokenizer import Tokenizer, TokenizerError
from src.models.command_window.tokenizer.token import TokenType


# ─────────────────────────────────────────────────────────────
# Operadores binários básicos
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text, ops", [
    ("1+2", ["+"]),
    ("3-4", ["-"]),
    ("5*6", ["*"]),
    ("8/2", ["/"]),
    ("7%3", ["%"]),
])
def test_basic_binary_operators(text, ops):
    tokens = Tokenizer(text).tokenize()
    operators = [t.raw for t in tokens if t.type is TokenType.OPERATOR]
    assert operators == ops


# ─────────────────────────────────────────────────────────────
# Precedência não importa no tokenizer, apenas ordem
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text, ops", [
    ("1+2*3", ["+", "*"]),
    ("4*5-6", ["*", "-"]),
    ("7+8/4", ["+", "/"]),
    ("9-3%2", ["-", "%"]),
])
def test_operator_order(text, ops):
    tokens = Tokenizer(text).tokenize()
    operators = [t.raw for t in tokens if t.type is TokenType.OPERATOR]
    assert operators == ops


# ─────────────────────────────────────────────────────────────
# Parênteses simples
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "(1)",
    "(1+2)",
    "((3))",
    "(4*(5+6))",
])
def test_parentheses_tokens(text):
    tokens = Tokenizer(text).tokenize()
    lparens = [t for t in tokens if t.type is TokenType.LPAREN]
    rparens = [t for t in tokens if t.type is TokenType.RPAREN]
    assert len(lparens) == len(rparens)


# ─────────────────────────────────────────────────────────────
# Signed numbers em posições válidas
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text, expected", [
    ("-2", -2),
    ("+3", 3),
    ("(-4)", -4),
    ("(+5)", 5),
    ("1+-2", -2),
    ("1--2", -2),
])
def test_signed_numbers(text, expected):
    tokens = Tokenizer(text).tokenize()
    numbers = [t for t in tokens if t.type is TokenType.NUMBER]
    assert any(t.value == expected for t in numbers)


# ─────────────────────────────────────────────────────────────
# Signed NÃO deve engolir operador binário
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text, ops", [
    ("1+2", ["+"]),
    ("3-4", ["-"]),
    ("5*-6", ["*"]),
    ("7/-2", ["/"]),
])
def test_signed_does_not_hide_binary_operator(text, ops):
    tokens = Tokenizer(text).tokenize()
    operators = [t.raw for t in tokens if t.type is TokenType.OPERATOR]
    assert operators == ops


# ─────────────────────────────────────────────────────────────
# Identificadores e operadores
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text, idents, ops", [
    ("a+b", ["a", "b"], ["+"]),
    ("x-y", ["x", "y"], ["-"]),
    ("foo*bar", ["foo", "bar"], ["*"]),
    ("a+(-b)", ["a", "b"], ["+", "-"]),
])
def test_identifiers_and_operators(text, idents, ops):
    tokens = Tokenizer(text).tokenize()

    found_idents = [t.raw for t in tokens if t.type is TokenType.IDENTIFIER]
    found_ops = [t.raw for t in tokens if t.type is TokenType.OPERATOR]

    assert found_idents == idents
    assert found_ops == ops


# ─────────────────────────────────────────────────────────────
# Expressões combinadas (sem avaliar)
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "1+(2*3)",
    "-(a+2)",
    "a*(-b)",
    "3/-2",
    "2*(-1/-2*-1)",
    "-(-2+3)-(-5*-1*-2)",
])
def test_complex_expressions_tokenize(text):
    tokens = Tokenizer(text).tokenize()
    assert tokens[-1].type is TokenType.EOF
