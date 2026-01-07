from src.core.command_window.evaluator.evaluator import Evaluator
from src.core.command_window.tokenizer import Token, TokenType

def T(t, raw, value=None):
    return Token(t, raw, value=value, position=0)


def test_simple_addition():
    tokens = [
        T(TokenType.NUMBER, "1", 1),
        T(TokenType.OPERATOR, "+"),
        T(TokenType.NUMBER, "2", 2),
        T(TokenType.EOF, "")]
    assert Evaluator().evaluate(tokens) == 3

def test_operator_precedence():
    tokens = [
        T(TokenType.NUMBER, "2", 2),
        T(TokenType.OPERATOR, "+"),
        T(TokenType.NUMBER, "3", 3),
        T(TokenType.OPERATOR, "*"),
        T(TokenType.NUMBER, "4", 4),
        T(TokenType.EOF, "")]
    assert Evaluator().evaluate(tokens) == 14

def test_parentheses_override_precedence():
    tokens = [
        T(TokenType.LPAREN, "("),
        T(TokenType.NUMBER, "2", 2),
        T(TokenType.OPERATOR, "+"),
        T(TokenType.NUMBER, "3", 3),
        T(TokenType.RPAREN, ")"),
        T(TokenType.OPERATOR, "*"),
        T(TokenType.NUMBER, "4", 4),
        T(TokenType.EOF, "")]
    assert Evaluator().evaluate(tokens) == 20

def test_unary_minus():
    tokens = [
        T(TokenType.OPERATOR, "-"),
        T(TokenType.NUMBER, "5", 5),
        T(TokenType.EOF, "")]
    assert Evaluator().evaluate(tokens) == -5



