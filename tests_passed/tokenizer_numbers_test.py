import pytest # type: ignore
from src.models.command_window.tokenizer.token import TokenType
from src.models.command_window.tokenizer.tokenizer import Tokenizer, TokenizerError

def test_decimal_number():
    tokenizer = Tokenizer("123")
    tokens = tokenizer.tokenize()
    assert tokens[0].type == TokenType.NUMBER
    assert tokens[0].value == "123"
    assert tokens[1].type == TokenType.EOF

def test_hex_number():
    tokenizer = Tokenizer("0x1A")
    tokens = tokenizer.tokenize()
    assert tokens[0].type == TokenType.NUMBER
    assert tokens[0].value == "0x1A"
    assert tokens[1].type == TokenType.EOF

def test_binary_number():
    tokenizer = Tokenizer("0b101")
    tokens = tokenizer.tokenize()
    assert tokens[0].type == TokenType.NUMBER
    assert tokens[0].value == "0b101"
    assert tokens[1].type == TokenType.EOF

def test_numbers_with_operators():
    tokenizer = Tokenizer("123 + 0x1A - 0b101")
    tokens = tokenizer.tokenize()
    print('\n', tokens, '\n')
    expected_types = [
        TokenType.NUMBER, TokenType.OPERATOR,
        TokenType.NUMBER, TokenType.OPERATOR,
        TokenType.NUMBER, TokenType.EOF
    ]
    actual_types = [t.type for t in tokens]
    print(actual_types, '\n')
    assert actual_types == expected_types
