import pytest # type: ignore
from src.models.command_window.context import Context

def test_context_using_public_methods():
    ctx = Context()

    def print_history(label):
        print(f"{label}: {ctx._Context__history}") 

    print("Variável ANS inicial:", ctx.get_variable("ANS"))
    print_history("Histórico inicial")
    assert ctx.get_variable("ANS") == 0
    assert ctx._Context__history == []

    ctx.set_variable("x", 42)
    ctx.set_variable("pi", 3.14)
    print("Variáveis após set_variable:")
    print("x =", ctx.get_variable("x"))
    print("pi =", ctx.get_variable("pi"))
    print("ANS =", ctx.get_variable("ANS"))
    assert ctx.get_variable("x") == 42
    assert ctx.get_variable("pi") == 3.14
    assert ctx.get_variable("ANS") == 0

    ctx.add_to_history("x = 42")
    ctx.add_to_history("pi = 3.14")
    ctx.add_to_history("ANS + x")
    print_history("Histórico após adições")
    assert ctx._Context__history == ["x = 42", "pi = 3.14", "ANS + x"]

    ctx.remove_history_line(1)  # remove "pi = 3.14"
    print_history("Histórico após remoção da linha 1")
    assert ctx._Context__history == ["x = 42", "ANS + x"]

    ctx.remove_history_line(10)
    ctx.remove_history_line(-1)
    print_history("Histórico após tentativas de remoção inválidas")
    assert ctx._Context__history == ["x = 42", "ANS + x"]

    ctx.clear_history()
    print_history("Histórico após limpeza")
    assert ctx._Context__history == []
