import pytest # type: ignore
from src.models.command_window.evaluator.assignment import AssignmentHandler
from src.models.command_window.context import Context
from src.models.command_window.tokenizer.token import Token, TokenType


def Tok(type, raw, value=None):
    return Token(type, raw, value) if value is not None else Token(type, raw)

@pytest.mark.parametrize(
    "initial_vars, tokens, expected, updated_var",
    [
        (
            {"a": 2},
            [
                Tok(TokenType.IDENTIFIER, "a"),
                Tok(TokenType.OPERATOR, "="),
                Tok(TokenType.NUMBER, "2", 2),
                Tok(TokenType.OPERATOR, "*"),
                Tok(TokenType.IDENTIFIER, "a"),
                Tok(TokenType.EOF, "")
            ],
            4,
            "a"
        ),
        (
            {"a": 2},
            [
                Tok(TokenType.IDENTIFIER, "a"),
                Tok(TokenType.OPERATOR, "="),
                Tok(TokenType.IDENTIFIER, "a"),
                Tok(TokenType.OPERATOR, "+"),
                Tok(TokenType.NUMBER, "2", 2),
                Tok(TokenType.EOF, "")
            ],
            4,
            "a"
        ),
        (
            {"a": 2, "b": 3},
            [
                Tok(TokenType.IDENTIFIER, "a"),
                Tok(TokenType.OPERATOR, "="),
                Tok(TokenType.IDENTIFIER, "a"),
                Tok(TokenType.OPERATOR, "+"),
                Tok(TokenType.IDENTIFIER, "b"),
                Tok(TokenType.OPERATOR, "+"),
                Tok(TokenType.NUMBER, "1", 1),
                Tok(TokenType.EOF, "")
            ],
            6,
            "a"
        ),
        (
            {"a": 2, "b": 3},
            [
                Tok(TokenType.IDENTIFIER, "c"),
                Tok(TokenType.OPERATOR, "="),
                Tok(TokenType.IDENTIFIER, "a"),
                Tok(TokenType.OPERATOR, "+"),
                Tok(TokenType.IDENTIFIER, "b"),
                Tok(TokenType.OPERATOR, "+"),
                Tok(TokenType.NUMBER, "5", 5),
                Tok(TokenType.EOF, "")
            ],
            10,
            "c"
        ),
    ]
)
def test_assignments_do_not_touch_ans(initial_vars, tokens, expected, updated_var):
    ctx = Context()
    for k, v in initial_vars.items():
        ctx.set_variable(k, v)

    handler = AssignmentHandler(ctx)

    result = handler.handle(tokens)

    assert result == expected
    assert ctx.get_variable(updated_var) == expected
    assert ctx.get_variable("ANS") == 0

def test_expression_updates_ans_only():
    ctx = Context()
    ctx.set_variable("a", 2)
    ctx.set_variable("b", 3)
    ctx.set_variable("c", 4)

    handler = AssignmentHandler(ctx)

    tokens = [
        Tok(TokenType.NUMBER, "2", 2),
        Tok(TokenType.OPERATOR, "*"),
        Tok(TokenType.IDENTIFIER, "a"),
        Tok(TokenType.OPERATOR, "*"),
        Tok(TokenType.IDENTIFIER, "c"),
        Tok(TokenType.OPERATOR, "*"),
        Tok(TokenType.IDENTIFIER, "b"),
        Tok(TokenType.OPERATOR, "+"),
        Tok(TokenType.IDENTIFIER, "a"),
        Tok(TokenType.OPERATOR, "+"),
        Tok(TokenType.NUMBER, "6", 6),
        Tok(TokenType.OPERATOR, "<<"),
        Tok(TokenType.NUMBER, "2", 2),
        Tok(TokenType.OPERATOR, "-"),
        Tok(TokenType.LPAREN, "("),
        Tok(TokenType.OPERATOR, "-"),
        Tok(TokenType.NUMBER, "4", 4),
        Tok(TokenType.OPERATOR, "+"),
        Tok(TokenType.NUMBER, "2", 2),
        Tok(TokenType.OPERATOR, "/"),
        Tok(TokenType.OPERATOR, "-"),
        Tok(TokenType.NUMBER, "1", 1),
        Tok(TokenType.RPAREN, ")"),
        Tok(TokenType.OPERATOR, "+"),
        Tok(TokenType.NUMBER, "5", 5),
        Tok(TokenType.OPERATOR, "*"),
        Tok(TokenType.LPAREN, "("),
        Tok(TokenType.IDENTIFIER, "a"),
        Tok(TokenType.OPERATOR, "=="),
        Tok(TokenType.IDENTIFIER, "b"),
        Tok(TokenType.RPAREN, ")"),
        Tok(TokenType.EOF, "")]

    result = handler.handle(tokens)

    assert ctx.get_variable("ANS") == result
    assert ctx.get_variable("a") == 2
    assert ctx.get_variable("b") == 3
    assert ctx.get_variable("c") == 4

def test_assignment_can_use_ans_but_does_not_modify_it():
    ctx = Context()
    ctx.set_variable("a", 2)
    ctx.set_variable("b", 3)
    ctx.set_variable("c", 4)
    ctx.set_variable("ANS", 10)

    handler = AssignmentHandler(ctx)

    tokens = [
        Tok(TokenType.IDENTIFIER, "c"),
        Tok(TokenType.OPERATOR, "="),
        Tok(TokenType.NUMBER, "2", 2),
        Tok(TokenType.OPERATOR, "*"),
        Tok(TokenType.IDENTIFIER, "a"),
        Tok(TokenType.OPERATOR, "*"),
        Tok(TokenType.IDENTIFIER, "c"),
        Tok(TokenType.OPERATOR, "*"),
        Tok(TokenType.IDENTIFIER, "b"),
        Tok(TokenType.OPERATOR, "+"),
        Tok(TokenType.IDENTIFIER, "ANS"),
        Tok(TokenType.EOF, "")]

    result = handler.handle(tokens)

    assert ctx.get_variable("c") == result
    assert ctx.get_variable("ANS") == 10

def test_expression_using_ans():
    ctx = Context()
    ctx.set_variable("a", 2)
    ctx.set_variable("b", 3)
    ctx.set_variable("ANS", 4)

    handler = AssignmentHandler(ctx)

    tokens = [
        Tok(TokenType.NUMBER, "2", 2),
        Tok(TokenType.OPERATOR, "*"),
        Tok(TokenType.IDENTIFIER, "a"),
        Tok(TokenType.OPERATOR, "*"),
        Tok(TokenType.IDENTIFIER, "ANS"),
        Tok(TokenType.OPERATOR, "+"),
        Tok(TokenType.IDENTIFIER, "ANS"),
        Tok(TokenType.OPERATOR, "-"),
        Tok(TokenType.NUMBER, "5", 5),
        Tok(TokenType.OPERATOR, "*"),
        Tok(TokenType.IDENTIFIER, "b"),
        Tok(TokenType.EOF, "")]

    result = handler.handle(tokens)

    assert result == 5
    assert ctx.get_variable("ANS") == 5
    assert ctx.get_variable("a") == 2
    assert ctx.get_variable("b") == 3


