import pytest # type: ignore
from src.core.command_window.evaluator.evaluator import Evaluator
from src.core.command_window.tokenizer.token import TokenType, Token as T

def Tok(type, raw, value=None):
    return T(type, raw, value) if value is not None else T(type, raw)

@pytest.mark.parametrize("tokens, expected", [
    ([Tok(TokenType.NUMBER, "10", 10), Tok(TokenType.OPERATOR, "/"), Tok(TokenType.NUMBER, "3", 3), Tok(TokenType.EOF, "")], 10/3),

    ([Tok(TokenType.NUMBER, "0b1010", 0b1010), Tok(TokenType.OPERATOR, "&"), Tok(TokenType.NUMBER, "0b0110", 0b0110), Tok(TokenType.EOF, "")], 0b0010),
    ([Tok(TokenType.NUMBER, "0xF", 0xF), Tok(TokenType.OPERATOR, "|"), Tok(TokenType.NUMBER, "0x1", 0x1), Tok(TokenType.EOF, "")], 0xF),
    
    ([Tok(TokenType.NUMBER, "5", 5), Tok(TokenType.OPERATOR, "=="), Tok(TokenType.NUMBER, "5", 5), Tok(TokenType.EOF, "")], 1),
    ([Tok(TokenType.NUMBER, "5", 5), Tok(TokenType.OPERATOR, "!="), Tok(TokenType.NUMBER, "3", 3), Tok(TokenType.EOF, "")], 1),
    
    ([Tok(TokenType.NUMBER, "2.5", 2.5), Tok(TokenType.OPERATOR, "<<"), Tok(TokenType.NUMBER, "2", 2), Tok(TokenType.EOF, "")], int(2.5) << 2),
    ([Tok(TokenType.NUMBER, "7", 7), Tok(TokenType.OPERATOR, ">>"), Tok(TokenType.NUMBER, "1", 1), Tok(TokenType.EOF, "")], 3),
    
    ([Tok(TokenType.OPERATOR, "-"), Tok(TokenType.NUMBER, "2", 2), Tok(TokenType.OPERATOR, "**"), Tok(TokenType.NUMBER, "3", 3), Tok(TokenType.EOF, "")], -(2**3)),

    #FAILED
    ([Tok(TokenType.NUMBER, "2", 2), Tok(TokenType.OPERATOR, "*"), Tok(TokenType.LPAREN, "("), Tok(TokenType.OPERATOR, "-"), Tok(TokenType.NUMBER, "3", 3), Tok(TokenType.OPERATOR, "+"), Tok(TokenType.NUMBER, "5", 5), Tok(TokenType.RPAREN, ")"), Tok(TokenType.OPERATOR, "**"), Tok(TokenType.NUMBER, "2", 2), Tok(TokenType.EOF, "")], (2 * ((-3 + 5) ** 2)))])
def test_complex_evaluator(tokens, expected):
    assert Evaluator().evaluate(tokens) == expected

@pytest.mark.parametrize("tokens, expected", [(
    [Tok(TokenType.NUMBER, "2", 2), Tok(TokenType.OPERATOR, "*"), Tok(TokenType.LPAREN, "("), Tok(TokenType.OPERATOR, "-"), Tok(TokenType.NUMBER, "3", 3), Tok(TokenType.OPERATOR, "+"), Tok(TokenType.NUMBER, "5", 5), Tok(TokenType.RPAREN, ")"), Tok(TokenType.OPERATOR, "**"), Tok(TokenType.NUMBER, "2", 2), Tok(TokenType.EOF, "")], (2 * ((-3 + 5) ** 2))),

    ([Tok(TokenType.NUMBER, "2", 2), Tok(TokenType.OPERATOR, "*"), Tok(TokenType.LPAREN, "("), Tok(TokenType.NUMBER, "3", 3), Tok(TokenType.OPERATOR, "+"), Tok(TokenType.OPERATOR, "-"), Tok(TokenType.NUMBER, "1", 1),
    Tok(TokenType.RPAREN, ")"), Tok(TokenType.EOF, "")], 2*(3+-1))])
def test_failing_eval(tokens, expected):
        assert Evaluator().evaluate(tokens) == expected

