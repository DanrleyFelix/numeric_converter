import pytest #type: ignore

from src.core.command_window.tokenizer.token import TokenType
from src.core.command_window.tokenizer.tokenizer import Tokenizer, TokenizerError

@pytest.mark.parametrize("text, ops", [
    ("1+2", ["+"]),
    ("3-4", ["-"]),
    ("5*6", ["*"]),
    ("8/2", ["/"]),
    ("7%3", ["%"])])
def test_basic_binary_operators(text, ops):
    tokens = Tokenizer(text).tokenize()
    operators = [t.raw for t in tokens if t.type is TokenType.OPERATOR]
    assert operators == ops

@pytest.mark.parametrize("text, ops", [
    ("1+2*3", ["+", "*"]),
    ("4*5-6", ["*", "-"]),
    ("7+8/4", ["+", "/"]),
    ("9-3%2", ["-", "%"])])
def test_operator_order(text, ops):
    tokens = Tokenizer(text).tokenize()
    operators = [t.raw for t in tokens if t.type is TokenType.OPERATOR]
    assert operators == ops

@pytest.mark.parametrize("text, lcount, rcount", [
    ("(1)", 1, 1),
    ("(1+2)", 1, 1),
    ("((3))", 2, 2),
    ("(4*(5+6))", 2, 2)])
def test_parentheses_tokens(text, lcount, rcount):
    tokens = Tokenizer(text).tokenize()

    lparens = [t for t in tokens if t.type is TokenType.LPAREN]
    rparens = [t for t in tokens if t.type is TokenType.RPAREN]

    assert len(lparens) == lcount
    assert len(rparens) == rcount

@pytest.mark.parametrize("text, ops", [
    ("-1", ["-"]),
    ("3*-4", ["*", "-"]),
    ("7/-2", ["/", "-"]),
    ("a+(-b)", ["+", "-"])])
def test_sign_is_always_operator(text, ops):
    tokens = Tokenizer(text).tokenize()
    operators = [t.raw for t in tokens if t.type is TokenType.OPERATOR]
    assert operators == ops

@pytest.mark.parametrize("text, idents, ops", [
    ("a+b", ["a", "b"], ["+"]),
    ("x-y", ["x", "y"], ["-"]),
    ("foo*bar", ["foo", "bar"], ["*"]),
    ("a+(-b)", ["a", "b"], ["+", "-"])])
def test_identifiers_and_operators(text, idents, ops):
    tokens = Tokenizer(text).tokenize()

    found_idents = [t.raw for t in tokens if t.type is TokenType.IDENTIFIER]
    found_ops = [t.raw for t in tokens if t.type is TokenType.OPERATOR]

    assert found_idents == idents
    assert found_ops == ops

@pytest.mark.parametrize("text, value", [
    ("10", 10),
    ("0b1010", 10),
    ("0xFF", 255),
    ("0x10", 16)])
def test_number_bases(text, value):
    tokens = Tokenizer(text).tokenize()
    number = next(t for t in tokens if t.type is TokenType.NUMBER)
    assert number.value == value

@pytest.mark.parametrize("text, value", [
    ("1.5", 1.5),
    ("0.25", 0.25),
    ("10.0", 10.0)])
def test_decimal_floats(text, value):
    tokens = Tokenizer(text).tokenize()
    number = next(t for t in tokens if t.type is TokenType.NUMBER)
    assert number.value == value

@pytest.mark.parametrize("text", [
    "1+(2*3)",
    "-(a+2)",
    "a*(-b)",
    "3/-2",
    "2*(-1/-2*-1)",
    "-(-2+3)-(-5*-1*-2)"])
def test_complex_expressions_tokenize(text):
    tokens = Tokenizer(text).tokenize()
    assert tokens[-1].type is TokenType.EOF

@pytest.mark.parametrize("text", [
    "0b102",
    "0xFG",
    "1. "])
def test_invalid_numbers_raise(text):
    with pytest.raises(TokenizerError):
        Tokenizer(text).tokenize()





