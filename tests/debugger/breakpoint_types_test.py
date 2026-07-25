import pytest

from src.core.debugger.breakpoints.conditions import (
    parse_register_condition,
    register_aliases,
)
from src.core.debugger.breakpoints.types import (
    breakpoint_type_display,
    normalize_breakpoint_type,
)
from src.core.debugger.models.session import DebuggerSessionState
from helpers import BASE, END, configured_debugger


def test_breakpoint_types_normalize_combinations_and_reject_register_mixing():
    """Accept address combinations without introducing a synthetic all type."""

    assert normalize_breakpoint_type("execution") == "execution"
    assert normalize_breakpoint_type("exec") == "execution"
    assert normalize_breakpoint_type("w | r") == "write || read"
    assert normalize_breakpoint_type("execution || write") == "write || execution"
    assert normalize_breakpoint_type("write or exec") == "write || execution"
    assert (
        normalize_breakpoint_type("write || read || execution")
        == "write || read || execution"
    )
    assert normalize_breakpoint_type("register") == "register"
    assert normalize_breakpoint_type("reg") == "register"
    assert breakpoint_type_display("write || execution") == "w | exec"
    for invalid in ("all", "register || read", "write ||", "write || write"):
        with pytest.raises(ValueError):
            normalize_breakpoint_type(invalid)


def test_register_condition_parser_supports_comparisons_and_logical_groups():
    """Parse all requested comparison operators with AND before OR."""

    debugger = configured_debugger("nop")
    aliases = register_aliases(debugger.registers.descriptors)
    condition = parse_register_condition(
        "$v0 > 0x200 & $v0 <= 500 || $s2 != 0",
        aliases,
    )
    assert condition.evaluate({**debugger.registers.snapshot(), "s2": 1})
    assert not condition.evaluate({**debugger.registers.snapshot(), "v0": 0x300})
    assert parse_register_condition("$v0 >= 0 & $v0 < 1", aliases).evaluate(
        debugger.registers.snapshot()
    )
    assert parse_register_condition("$v0 == 0", aliases).evaluate(
        debugger.registers.snapshot()
    )
    cross_register = parse_register_condition(
        "$a3 >= 0x2 or $t3 == 0x0",
        aliases,
    )
    assert cross_register.evaluate(debugger.registers.snapshot())
    assert parse_register_condition(
        "$a3 == 0 && $t3 == 0",
        aliases,
    ).evaluate(debugger.registers.snapshot())
    assert parse_register_condition(
        "$a3 == 0 and $t3 == 0",
        aliases,
    ).evaluate(debugger.registers.snapshot())


@pytest.mark.parametrize(
    ("operation", "instructions", "expected_pc", "expected_instruction"),
    (
        (
            "write",
            ("addiu $t0, $zero, 2", "sw $t0, 0($sp)", "nop"),
            BASE + 8,
            "sw $t0, 0($sp)",
        ),
        (
            "read",
            ("lw $t0, 0($sp)", "nop"),
            BASE + 4,
            "lw $t0, 0($sp)",
        ),
    ),
)
def test_memory_breakpoints_pause_after_the_causative_instruction(
    operation,
    instructions,
    expected_pc,
    expected_instruction,
):
    """Pause on read/write hooks and retain the instruction causing the access."""

    debugger = configured_debugger(*instructions)
    debugger.add_breakpoint(END - 3, breakpoint_type=operation)

    debugger.run(limit=10)

    breakpoint = debugger.breakpoints[0]
    assert debugger.state == DebuggerSessionState.PAUSED
    assert debugger.pc == expected_pc
    assert breakpoint.triggered
    assert breakpoint.hit_instruction == expected_instruction


def test_combined_access_breakpoint_and_default_execution_behavior():
    """Preserve execution defaults while allowing equivalent combined access."""

    debugger = configured_debugger("lw $t0, 0($sp)", "nop")
    combined = debugger.add_breakpoint(
        END - 3,
        breakpoint_type="execution || read || write",
    )
    assert combined.breakpoint_type == "write || read || execution"
    debugger.run(limit=10)
    assert debugger.pc == BASE + 4

    execution = configured_debugger("nop", "nop")
    breakpoint = execution.toggle_breakpoint(BASE + 4)
    assert breakpoint.breakpoint_type == "execution"
    assert breakpoint.where == f"0x{BASE + 4:08X}"
    execution.run(limit=10)
    assert execution.pc == BASE + 4


def test_register_breakpoint_fires_only_when_condition_becomes_true():
    """Record the instruction that changes a false register condition to true."""

    debugger = configured_debugger("addiu $s2, $zero, 2", "nop")
    breakpoint = debugger.add_register_breakpoint("$s2 == 0x2")

    debugger.run(limit=10)

    triggered = next(
        item for item in debugger.breakpoints if item.identifier == breakpoint.identifier
    )
    assert debugger.state == DebuggerSessionState.PAUSED
    assert debugger.pc == BASE + 4
    assert triggered.triggered
    assert triggered.hit_instruction == "addiu $s2, $zero, 2"
    assert triggered.address is None
    assert triggered.breakpoint_type == "register"


def test_register_breakpoint_rejects_unknown_registers():
    """Keep invalid register conditions out of retained breakpoint metadata."""

    debugger = configured_debugger("nop")
    with pytest.raises(ValueError):
        debugger.add_register_breakpoint("$missing == 1")
    assert debugger.breakpoints == ()


def test_where_edits_revalidate_without_turning_syntax_errors_into_failures():
    """Apply valid edits and retain invalid WHERE input as inactive metadata."""

    debugger = configured_debugger("nop", "nop")
    breakpoint = debugger.add_breakpoint(BASE)
    debugger.set_breakpoint_where(breakpoint.identifier, f"0x{BASE + 4:X}")
    moved = debugger.breakpoints[0]
    assert moved.address == BASE + 4
    assert moved.where == f"0x{BASE + 4:08X}"

    debugger.set_breakpoint_type(moved.identifier, "reg")
    converted = debugger.breakpoints[0]
    assert converted.breakpoint_type == "register"
    assert not converted.valid
    assert debugger.events[-1].level == "Syntax Error"
    assert "column 1" in debugger.events[-1].message

    debugger.set_breakpoint_where(converted.identifier, "$s2 == 0x2")
    assert debugger.breakpoints[0].valid
    assert debugger.state == DebuggerSessionState.READY
