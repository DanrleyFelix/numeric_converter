import pytest # type: ignore

from src.models.command_window.tokenizer.tokenizer import Tokenizer, TokenizerError
from src.models.command_window.tokenizer.token import TokenType


@pytest.mark.parametrize("text, value", [("0b0", 0), ("0b1", 1), ("0b1010", 10), ("0xA", 10), ("0x10", 16), ("0xFF", 255)])
def test_numeric_bases(text, value):
    tokens = Tokenizer(text).tokenize()
    assert tokens[0].type is TokenType.NUMBER
    assert tokens[0].value == value

@pytest.mark.parametrize("text", ["0b10 + 2", "0xA * 0b11", "(0x10 + 4) / 0b10"])
def test_mixed_bases_expressions(text):
    tokens = Tokenizer(text).tokenize()
    numbers = [t for t in tokens if t.type is TokenType.NUMBER]
    assert len(numbers) >= 2
    assert tokens[-1].type is TokenType.EOF

@pytest.mark.parametrize("text, value", [("0.1", 0.1), ("1.0", 1.0), ("3.14", 3.14), ("10.25", 10.25)])
def test_decimal_floats(text, value):
    tokens = Tokenizer(text).tokenize()
    assert tokens[0].type is TokenType.NUMBER
    assert tokens[0].value == value

@pytest.mark.parametrize("text, value", [("-1.5", -1.5), ("+2.25", 2.25), ("(-3.75)", -3.75)])
def test_signed_floats(text, value):
    tokens = Tokenizer(text).tokenize()
    numbers = [t for t in tokens if t.type is TokenType.NUMBER]
    assert numbers[0].value == value

@pytest.mark.parametrize("text", ["0b", "0x", "0b102", "0xFG", "1.", ".5"])
def test_invalid_numbers(text):
    with pytest.raises(TokenizerError):
        Tokenizer(text).tokenize()

@pytest.mark.parametrize("text", ["@", "$", "#"])
def test_invalid_tokens(text):
    with pytest.raises(TokenizerError):
        Tokenizer(text).tokenize()

@pytest.mark.parametrize("text", ["1+2+3+4+5+6+7+8+9", "((((((10))))))", "a+b*c-d/e+f%g", "-(a+2)*(-5/-1)+(-2*(-2+3))", "-(-2+3)-(-5*-1*-2)"])
def test_large_expressions(text):
    tokens = Tokenizer(text).tokenize()
    assert tokens[-1].type is TokenType.EOF
    assert len(tokens) > 1

@pytest.mark.parametrize("text", ["1+-2+-3", "5--4--3", "10*-2*-3"])
def test_multiple_signed_numbers(text):
    tokens = Tokenizer(text).tokenize()
    numbers = [t for t in tokens if t.type is TokenType.NUMBER]
    assert len(numbers) >= 2
