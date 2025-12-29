import pytest #type: ignore

from src.models.command_window.tokenizer.token import TokenType
from src.models.command_window.tokenizer.tokenizer import Tokenizer, TokenizerError

@pytest.mark.parametrize("text", [
    "",
    " ",
    "   ",
    "\n",
    "\t",
    " \n\t  ",
])
def test_whitespace_only(text):
    tokens = Tokenizer(text).tokenize()

    assert len(tokens) == 1
    assert tokens[0].type is TokenType.EOF

@pytest.mark.parametrize("text, expected", [
    ("0", 0),
    ("1", 1),
    ("42", 42),
    ("123456", 123456),
])
def test_decimal_integers(text, expected):
    tokens = Tokenizer(text).tokenize()

    assert tokens[0].type is TokenType.NUMBER
    assert tokens[0].raw == text
    assert tokens[0].value == expected
    assert tokens[1].type is TokenType.EOF

@pytest.mark.parametrize("text, expected", [
    ("+0", 0),
    ("-0", 0),
    ("+1", 1),
    ("-1", -1),
    ("+42", 42),
    ("-42", -42),
])
def test_signed_decimal_integers(text, expected):
    tokens = Tokenizer(text).tokenize()

    assert tokens[0].type is TokenType.NUMBER
    assert tokens[0].raw == text
    assert tokens[0].value == expected
    assert tokens[1].type is TokenType.EOF

@pytest.mark.parametrize("text, expected", [
    ("0.0", 0.0),
    ("1.5", 1.5),
    ("10.25", 10.25),
    ("123.456", 123.456),
])
def test_decimal_floats(text, expected):
    tokens = Tokenizer(text).tokenize()

    assert tokens[0].type is TokenType.NUMBER
    assert tokens[0].raw == text
    assert tokens[0].value == expected
    assert tokens[1].type is TokenType.EOF

@pytest.mark.parametrize("text, expected", [
    ("+1.5", 1.5),
    ("-1.5", -1.5),
    ("+0.25", 0.25),
    ("-0.25", -0.25),
])
def test_signed_decimal_floats(text, expected):
    tokens = Tokenizer(text).tokenize()

    assert tokens[0].type is TokenType.NUMBER
    assert tokens[0].raw == text
    assert tokens[0].value == expected
    assert tokens[1].type is TokenType.EOF

@pytest.mark.parametrize("text, expected", [
    ("0b0", 0),
    ("0b1", 1),
    ("0b10", 2),
    ("0b1010", 10),
])
def test_binary_integers(text, expected):
    tokens = Tokenizer(text).tokenize()

    assert tokens[0].type is TokenType.NUMBER
    assert tokens[0].raw == text
    assert tokens[0].value == expected
    assert tokens[1].type is TokenType.EOF


@pytest.mark.parametrize("text, expected", [
    ("+0b10", 2),
    ("-0b10", -2),
])
def test_signed_binary_integers(text, expected):
    tokens = Tokenizer(text).tokenize()

    assert tokens[0].type is TokenType.NUMBER
    assert tokens[0].raw == text
    assert tokens[0].value == expected
    assert tokens[1].type is TokenType.EOF


@pytest.mark.parametrize("text, expected", [
    ("0x0", 0),
    ("0xA", 10),
    ("0x10", 16),
    ("0xFF", 255),
])
def test_hexadecimal_integers(text, expected):
    tokens = Tokenizer(text).tokenize()

    assert tokens[0].type is TokenType.NUMBER
    assert tokens[0].raw == text
    assert tokens[0].value == expected
    assert tokens[1].type is TokenType.EOF


@pytest.mark.parametrize("text, expected", [
    ("+0xFF", 255),
    ("-0xFF", -255),
])
def test_signed_hexadecimal_integers(text, expected):
    tokens = Tokenizer(text).tokenize()

    assert tokens[0].type is TokenType.NUMBER
    assert tokens[0].raw == text
    assert tokens[0].value == expected
    assert tokens[1].type is TokenType.EOF

@pytest.mark.parametrize("text", [
    "0b",
    "0x",
    "1.",
    "0b102",
    "0xFG",
])
def test_invalid_numbers(text):
    with pytest.raises(TokenizerError):
        Tokenizer(text).tokenize()
