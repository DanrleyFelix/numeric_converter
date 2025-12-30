import pytest # type: ignore
from src.models.command_window.evaluator.assignment import AssignmentHandler
from src.models.command_window.context import Context
from src.models.command_window.tokenizer.token import Token, TokenType


def Tok(type, raw, value=None):
    return Token(type, raw, value) if value is not None else Token(type, raw)


def test_expression_without_assignment_updates_ans():
    ctx = Context()
    handler = AssignmentHandler(ctx)

    tokens = [
        Tok(TokenType.NUMBER, "2", 2),
        Tok(TokenType.OPERATOR, "+"),
        Tok(TokenType.NUMBER, "3", 3),
        Tok(TokenType.EOF, "")]

    result = handler.handle(tokens)

    assert result == 5
    assert ctx.get_variable("ANS") == 5

def test_expression_with_identifier():
    ctx = Context()
    ctx.set_variable("a", 10)

    handler = AssignmentHandler(ctx)

    tokens = [
        Tok(TokenType.NUMBER, "2", 2),
        Tok(TokenType.OPERATOR, "*"),
        Tok(TokenType.IDENTIFIER, "a"),
        Tok(TokenType.EOF, "")]

    result = handler.handle(tokens)

    assert result == 20
    assert ctx.get_variable("ANS") == 20
    assert ctx.get_variable("a") == 10 

def test_simple_assignment():
    ctx = Context()
    handler = AssignmentHandler(ctx)

    tokens = [
        Tok(TokenType.IDENTIFIER, "a"),
        Tok(TokenType.OPERATOR, "="),
        Tok(TokenType.NUMBER, "5", 5),
        Tok(TokenType.EOF, "")]

    result = handler.handle(tokens)

    assert result == 5
    assert ctx.get_variable("a") == 5
    assert ctx.get_variable("ANS") == 0

def test_assignment_with_expression():
    ctx = Context()
    handler = AssignmentHandler(ctx)

    tokens = [
        Tok(TokenType.IDENTIFIER, "x"),
        Tok(TokenType.OPERATOR, "="),
        Tok(TokenType.NUMBER, "2", 2),
        Tok(TokenType.OPERATOR, "+"),
        Tok(TokenType.NUMBER, "3", 3),
        Tok(TokenType.OPERATOR, "*"),
        Tok(TokenType.NUMBER, "4", 4),
        Tok(TokenType.EOF, "")]

    result = handler.handle(tokens)

    assert result == 14
    assert ctx.get_variable("x") == 14
    assert ctx.get_variable("ANS") == 0
