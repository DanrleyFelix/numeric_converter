import pytest # type: ignore
from src.models.command_window.tokenizer.token import TokenType
from src.models.command_window.tokenizer.tokenizer import Tokenizer, TokenizerError, UNARY_OPERATORS


@pytest.mark.parametrize("text, expected", [
    ("123", "123"),
    ("0b101", "0b101"),
    ("0x1A", "0x1A"),
])
def test_numbers(text, expected):
    tokenizer = Tokenizer(text)
    tokens = tokenizer.tokenize()
    assert tokens[0].type == TokenType.NUMBER
    assert tokens[0].value == expected
    assert tokens[1].type == TokenType.EOF


def test_identifiers():
    tokenizer = Tokenizer("var x _test")
    tokens = tokenizer.tokenize()
    values = [t.value for t in tokens if t.type == TokenType.IDENTIFIER]
    assert values == ["var", "x", "_test"]


def test_binary_operators():
    tokenizer = Tokenizer("x + y - z * 2 / 4 % 3 ** 2")
    tokens = tokenizer.tokenize()
    operators = [t.value for t in tokens if t.type == TokenType.OPERATOR]
    for op in ["+", "-", "*", "/", "%", "**"]:
        assert op in operators

@pytest.mark.parametrize("text,op", [
    ("+x", "+"),
    ("-y", "-"),
    ("!flag", "!"),
    ("~value", "~"),
    ("sqrt4", "sqrt")
])
def test_unary_operators(text, op):
    tokenizer = Tokenizer(text)
    tokens = tokenizer.tokenize()
    operator_token = tokens[0]
    assert operator_token.type == TokenType.OPERATOR
    assert operator_token.value == op
    assert operator_token.can_be_unary is True


def test_parentheses():
    tokenizer = Tokenizer("(a + b) * (c - d)")
    tokens = tokenizer.tokenize()
    lparen_count = sum(1 for t in tokens if t.type == TokenType.LPAREN)
    rparen_count = sum(1 for t in tokens if t.type == TokenType.RPAREN)
    assert lparen_count == 2
    assert rparen_count == 2


def test_complex_expression():
    expr = "x + 0b101 * (y - 0x1A) / sqrt4"
    tokenizer = Tokenizer(expr)
    tokens = tokenizer.tokenize()
    types = [t.type for t in tokens]
    expected_types = [
        TokenType.IDENTIFIER,  # x
        TokenType.OPERATOR,    # +
        TokenType.NUMBER,      # 0b101
        TokenType.OPERATOR,    # *
        TokenType.LPAREN,      # (
        TokenType.IDENTIFIER,  # y
        TokenType.OPERATOR,    # -
        TokenType.NUMBER,      # 0x1A
        TokenType.RPAREN,      # )
        TokenType.OPERATOR,    # /
        TokenType.OPERATOR,    # sqrt
        TokenType.NUMBER,      # 4
        TokenType.EOF
    ]
    assert types[0:len(expected_types)-1] == expected_types[:-1]
    assert tokens[-1].type == TokenType.EOF


def test_whitespace_skipping():
    tokenizer = Tokenizer("  \t123   +   x  ")
    tokens = tokenizer.tokenize()
    values = [t.value for t in tokens if t.type != TokenType.EOF]
    assert values == ["123", "+", "x"]


def test_unknown_token():
    tokenizer = Tokenizer("@")
    with pytest.raises(TokenizerError):
        tokenizer.tokenize()
