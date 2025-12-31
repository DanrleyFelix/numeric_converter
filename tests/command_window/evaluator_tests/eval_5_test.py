import pytest  # type: ignore
from src.models.command_window.evaluator.evaluator import Evaluator
from src.models.command_window.tokenizer.token import TokenType, Token as T

def Tok(type, raw, value=None):
    return T(type, raw, value) if value is not None else T(type, raw)

def test_shift_with_power():
    tokens = [
        Tok(TokenType.NUMBER, "200", 200),
        Tok(TokenType.OPERATOR, "<<"),
        Tok(TokenType.LPAREN, "("),
        Tok(TokenType.NUMBER, "2", 2),
        Tok(TokenType.OPERATOR, "**"),
        Tok(TokenType.NUMBER, "2", 2),
        Tok(TokenType.RPAREN, ")"),
        Tok(TokenType.EOF, "")
    ]

    assert Evaluator().evaluate(tokens) == (200 << (2 ** 2))

def test_outer_unary_does_not_affect_shift():
    tokens = [
        Tok(TokenType.OPERATOR, "-"),
        Tok(TokenType.LPAREN, "("),
        Tok(TokenType.NUMBER, "200", 200),
        Tok(TokenType.OPERATOR, "<<"),
        Tok(TokenType.LPAREN, "("),
        Tok(TokenType.NUMBER, "2", 2),
        Tok(TokenType.OPERATOR, "**"),
        Tok(TokenType.NUMBER, "2", 2),
        Tok(TokenType.RPAREN, ")"),
        Tok(TokenType.RPAREN, ")"),
        Tok(TokenType.EOF, "")
    ]

    assert Evaluator().evaluate(tokens) == -(200 << (2 ** 2))

def test_double_negation():
    tokens = [
        Tok(TokenType.OPERATOR, "-"),
        Tok(TokenType.OPERATOR, "-"),
        Tok(TokenType.NUMBER, "5", 5),
        Tok(TokenType.EOF, "")]

    assert Evaluator().evaluate(tokens) == 5

def test_unary_and_power():
    tokens = [
        Tok(TokenType.OPERATOR, "-"),
        Tok(TokenType.NUMBER, "2", 2),
        Tok(TokenType.OPERATOR, "**"),
        Tok(TokenType.NUMBER, "2", 2),
        Tok(TokenType.EOF, "")]
    assert Evaluator().evaluate(tokens) == -(2 ** 2)

def test_unary_applies_after_power():
    tokens = [
        Tok(TokenType.OPERATOR, "-"),
        Tok(TokenType.LPAREN, "("),
        Tok(TokenType.NUMBER, "2", 2),
        Tok(TokenType.OPERATOR, "**"),
        Tok(TokenType.NUMBER, "4", 4),
        Tok(TokenType.RPAREN, ")"),
        Tok(TokenType.OPERATOR, "<<"),
        Tok(TokenType.NUMBER, "1", 1),
        Tok(TokenType.EOF, "")]

    assert Evaluator().evaluate(tokens) == (-(2 ** 4) << 1)

def test_realistic_mixed_expression_fragment():
    tokens = [
        Tok(TokenType.OPERATOR, "-"),
        Tok(TokenType.LPAREN, "("),
        Tok(TokenType.NUMBER, "200", 200),
        Tok(TokenType.OPERATOR, "<<"),
        Tok(TokenType.LPAREN, "("),
        Tok(TokenType.NUMBER, "2", 2),
        Tok(TokenType.OPERATOR, "**"),
        Tok(TokenType.NUMBER, "2", 2),
        Tok(TokenType.RPAREN, ")"),
        Tok(TokenType.OPERATOR, "+"),
        Tok(TokenType.NUMBER, "1", 1),
        Tok(TokenType.RPAREN, ")"),
        Tok(TokenType.EOF, "")]

    assert Evaluator().evaluate(tokens) == -6400

def test_unary_parentheses_power_and_shift_complex():
    tokens = [
        Tok(TokenType.OPERATOR, "-"),
        Tok(TokenType.LPAREN, "("),
        Tok(TokenType.NUMBER, "0b11", 0b11),
        Tok(TokenType.OPERATOR, "+"),
        Tok(TokenType.NUMBER, "0xA", 0xA),
        Tok(TokenType.OPERATOR, "*"),
        Tok(TokenType.OPERATOR, "-"),
        Tok(TokenType.LPAREN, "("),
        Tok(TokenType.OPERATOR, "-"),
        Tok(TokenType.NUMBER, "2", 2),
        Tok(TokenType.OPERATOR, "**"),
        Tok(TokenType.NUMBER, "2", 2),
        Tok(TokenType.OPERATOR, "*"),
        Tok(TokenType.LPAREN, "("),
        Tok(TokenType.NUMBER, "3", 3),
        Tok(TokenType.OPERATOR, "/"),
        Tok(TokenType.OPERATOR, "-"),
        Tok(TokenType.NUMBER, "1", 1),
        Tok(TokenType.RPAREN, ")"),
        Tok(TokenType.RPAREN, ")"),    
        Tok(TokenType.OPERATOR, "+"),
        Tok(TokenType.LPAREN, "("),
        Tok(TokenType.NUMBER, "2", 2),
        Tok(TokenType.OPERATOR, "<<"),
        Tok(TokenType.LPAREN, "("),
        Tok(TokenType.NUMBER, "2", 2),
        Tok(TokenType.OPERATOR, "-"),
        Tok(TokenType.NUMBER, "1", 1),
        Tok(TokenType.RPAREN, ")"),
        Tok(TokenType.RPAREN, ")"),       
        Tok(TokenType.OPERATOR, "+"),
        Tok(TokenType.NUMBER, "5", 5),        
        Tok(TokenType.OPERATOR, "+"),
        Tok(TokenType.LPAREN, "("),
        Tok(TokenType.NUMBER, "5", 5),
        Tok(TokenType.OPERATOR, "<="),
        Tok(TokenType.NUMBER, "1", 1),
        Tok(TokenType.RPAREN, ")"),
        Tok(TokenType.OPERATOR, "+"),
        Tok(TokenType.LPAREN, "("),
        Tok(TokenType.NUMBER, "3", 3),
        Tok(TokenType.OPERATOR, "=="),
        Tok(TokenType.NUMBER, "3", 3),
        Tok(TokenType.RPAREN, ")"),
        Tok(TokenType.OPERATOR, "+"),
        Tok(TokenType.OPERATOR, "~"),
        Tok(TokenType.LPAREN, "("),
        Tok(TokenType.NUMBER, "0xA", 0xA),
        Tok(TokenType.OPERATOR, "^"),
        Tok(TokenType.NUMBER, "0b10", 0b10),
        Tok(TokenType.RPAREN, ")"),        
        Tok(TokenType.OPERATOR, "+"),
        Tok(TokenType.OPERATOR, "!"),
        Tok(TokenType.LPAREN, "("),
        Tok(TokenType.NUMBER, "0", 0),
        Tok(TokenType.RPAREN, ")"),  
        Tok(TokenType.OPERATOR, "+"),
        Tok(TokenType.NUMBER, "4.5", 4.5),
        Tok(TokenType.OPERATOR, "/"),
        Tok(TokenType.OPERATOR, "-"),
        Tok(TokenType.LPAREN, "("),
        Tok(TokenType.OPERATOR, "-"),
        Tok(TokenType.LPAREN, "("),
        Tok(TokenType.OPERATOR, "-"),
        Tok(TokenType.NUMBER, "0.5", 0.5),
        Tok(TokenType.OPERATOR, "*"),
        Tok(TokenType.OPERATOR, "-"),
        Tok(TokenType.NUMBER, "1", 1),
        Tok(TokenType.RPAREN, ")"),
        Tok(TokenType.RPAREN, ")"),    
        Tok(TokenType.OPERATOR, "+"),
        Tok(TokenType.LPAREN, "("),
        Tok(TokenType.LPAREN, "("),
        Tok(TokenType.NUMBER, "5", 5),
        Tok(TokenType.OPERATOR, "&&"),
        Tok(TokenType.NUMBER, "3", 3),
        Tok(TokenType.RPAREN, ")"),
        Tok(TokenType.OPERATOR, "||"),
        Tok(TokenType.LPAREN, "("),
        Tok(TokenType.NUMBER, "0", 0),
        Tok(TokenType.RPAREN, ")"),
        Tok(TokenType.RPAREN, ")"),    
        Tok(TokenType.RPAREN, ")"),
        Tok(TokenType.EOF, "")]
    assert int(Evaluator().evaluate(tokens)) == 103

def test_monster():
    tokens = [
        Tok(TokenType.OPERATOR, "-"),
        Tok(TokenType.NUMBER, "3", 3),
        Tok(TokenType.OPERATOR, "*"),
        Tok(TokenType.OPERATOR, "-"),
        Tok(TokenType.NUMBER, "2", 2),

        Tok(TokenType.OPERATOR, "+"),
        Tok(TokenType.LPAREN, "("),
        Tok(TokenType.NUMBER, "7", 7),
        Tok(TokenType.OPERATOR, "&"),
        Tok(TokenType.NUMBER, "4", 4),
        Tok(TokenType.RPAREN, ")"),

        Tok(TokenType.OPERATOR, "+"),
        Tok(TokenType.LPAREN, "("),
        Tok(TokenType.NUMBER, "3", 3),
        Tok(TokenType.OPERATOR, "&&"),
        Tok(TokenType.NUMBER, "2", 2),
        Tok(TokenType.RPAREN, ")"),
        Tok(TokenType.OPERATOR, "*"),
        Tok(TokenType.NUMBER, "5", 5),

        Tok(TokenType.OPERATOR, "-"),
        Tok(TokenType.OPERATOR, "~"),
        Tok(TokenType.LPAREN, "("),
        Tok(TokenType.NUMBER, "1", 1),
        Tok(TokenType.OPERATOR, "+"),
        Tok(TokenType.NUMBER, "2", 2),
        Tok(TokenType.RPAREN, ")"),

        Tok(TokenType.OPERATOR, "+"),
        Tok(TokenType.OPERATOR, "!"),
        Tok(TokenType.LPAREN, "("),
        Tok(TokenType.NUMBER, "0", 0),
        Tok(TokenType.RPAREN, ")"),

        Tok(TokenType.OPERATOR, "+"),
        Tok(TokenType.LPAREN, "("),
        Tok(TokenType.NUMBER, "4", 4),
        Tok(TokenType.OPERATOR, "||"),
        Tok(TokenType.NUMBER, "0", 0),
        Tok(TokenType.RPAREN, ")"),
        Tok(TokenType.OPERATOR, "*"),
        Tok(TokenType.NUMBER, "2", 2),

        Tok(TokenType.EOF, "")]
    assert int(Evaluator().evaluate(tokens)) == 33


    
