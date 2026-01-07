import pytest # type: ignore
from src.application.use_cases.evaluator_use_case import EvaluatorUseCase
from src.core.command_window.evaluator.evaluator import Evaluator
from src.core.command_window.context import cmd_window_context
from src.core.command_window.tokenizer.token import Token, TokenType


def Tok(type, raw, value=None):
    return Token(type, raw, value) if value is not None else Token(type, raw)


def test_expression_without_assignment_updates_ans():
    ctx = cmd_window_context
    ctx.clear_all()
    evaluator = Evaluator()
    handler = EvaluatorUseCase(evaluator)

    tokens = [
        Tok(TokenType.NUMBER, "2", 2),
        Tok(TokenType.OPERATOR, "+"),
        Tok(TokenType.NUMBER, "3", 3),
        Tok(TokenType.EOF, "")]

    result = handler.handle(tokens)

    assert result == 5
    assert ctx.get_variable("ANS") == 5

def test_expression_with_identifier():
    ctx = cmd_window_context
    ctx.clear_all()
    ctx.set_variable("a", 10)

    evaluator = Evaluator()
    handler = EvaluatorUseCase(evaluator)

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
    ctx = cmd_window_context
    ctx.clear_all()
    evaluator = Evaluator()
    handler = EvaluatorUseCase(evaluator)

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
    ctx = cmd_window_context
    ctx.clear_all()
    evaluator = Evaluator()
    handler = EvaluatorUseCase(evaluator)

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
