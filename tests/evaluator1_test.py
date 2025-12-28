import pytest # type: ignore
from src.models.command_window.tokenizer import Token, TokenType
from src.models.command_window.evaluator.evaluator import Evaluator


# helpers
def make_number_token(value):
    return Token(type=TokenType.NUMBER, value=value, raw=str(value), position=0)

def make_operator_token(op):
    return Token(type=TokenType.OPERATOR, value=None, raw=op, position=0)

def make_lparen_token():
    return Token(type=TokenType.LPAREN, value=None, raw="(", position=0)

def make_rparen_token():
    return Token(type=TokenType.RPAREN, value=None, raw=")", position=0)


def test_simple_arithmetic():
    evaluator = Evaluator()
    tokens = [
        make_number_token(2),
        make_operator_token("+"),
        make_number_token(3)
    ]
    assert evaluator.evaluate(tokens) == 5


def test_operator_precedence():
    evaluator = Evaluator()
    tokens = [
        make_number_token(2),
        make_operator_token("+"),
        make_number_token(3),
        make_operator_token("*"),
        make_number_token(4)
    ]
    # 2 + 3*4 = 14
    assert evaluator.evaluate(tokens) == 14


def test_parentheses():
    evaluator = Evaluator()
    tokens = [
        make_lparen_token(),
        make_number_token(2),
        make_operator_token("+"),
        make_number_token(3),
        make_rparen_token(),
        make_operator_token("*"),
        make_number_token(4)
    ]
    # (2+3)*4 = 20
    assert evaluator.evaluate(tokens) == 20


def test_nested_parentheses():
    evaluator = Evaluator()
    tokens = [
        make_lparen_token(),
        make_lparen_token(),
        make_number_token(2),
        make_operator_token("+"),
        make_number_token(3),
        make_rparen_token(),
        make_operator_token("*"),
        make_number_token(4),
        make_rparen_token()
    ]
    # ((2+3)*4) = 20
    assert evaluator.evaluate(tokens) == 20


def test_unary_operator():
    evaluator = Evaluator()
    tokens = [
        make_operator_token("-"),
        make_number_token(3),
        make_operator_token("+"),
        make_number_token(5)
    ]
    # -3 + 5 = 2
    assert evaluator.evaluate(tokens) == 2


def test_complex_expression():
    evaluator = Evaluator()
    tokens = [
        make_number_token(2),
        make_operator_token("+"),
        make_lparen_token(),
        make_number_token(3),
        make_operator_token("*"),
        make_number_token(4),
        make_rparen_token(),
        make_operator_token("-"),
        make_number_token(5)
    ]
    # 2 + (3*4) - 5 = 9
    assert evaluator.evaluate(tokens) == 9


def test_unary_with_parentheses():
    evaluator = Evaluator()
    tokens = [
        make_operator_token("-"),
        make_lparen_token(),
        make_number_token(3),
        make_operator_token("+"),
        make_number_token(5),
        make_rparen_token()
    ]
    # -(3+5) = -8
    assert evaluator.evaluate(tokens) == -8
