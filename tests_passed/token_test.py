import pytest # type: ignore
from src.models.command_window.tokenizer import Token, TokenType 

def test_token_type_enum():
    # Verifica se todos os tipos existem
    assert hasattr(TokenType, "NUMBER")
    assert hasattr(TokenType, "IDENTIFIER")
    assert hasattr(TokenType, "OPERATOR")
    assert hasattr(TokenType, "LPAREN")
    assert hasattr(TokenType, "RPAREN")
    assert hasattr(TokenType, "EOF")
    
    # Verifica se os valores são distintos
    values = [t.value for t in TokenType]
    assert len(values) == len(set(values))


def test_token_creation():
    token = Token(
        type=TokenType.NUMBER,
        value=42,
        raw="42",
        position=0,
        can_be_unary=True)
    
    assert token.type == TokenType.NUMBER
    assert token.value == 42
    assert token.raw == "42"
    assert token.position == 0
    assert token.can_be_unary is True


def test_token_default_can_be_unary():
    token = Token(
        type=TokenType.IDENTIFIER,
        value="x",
        raw="x",
        position=1)
    # O default deve ser False
    assert token.can_be_unary is False
