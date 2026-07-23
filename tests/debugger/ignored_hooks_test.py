from helpers import BASE, configured_debugger

import pytest

from src.core.debugger.models.session import DebuggerError, DebuggerSessionState


def test_ignored_instruction_advances_as_nop_and_is_counted():
    debugger = configured_debugger("addiu $t0, $zero, 9", "nop")
    debugger.toggle_ignored_instruction(BASE)

    debugger.step()

    assert debugger.pc == BASE + 4
    assert debugger.registers.read("t0") == 0
    assert debugger.statistics.executed[BASE] == 1
    assert debugger.statistics.ignored[BASE] == 1


def test_ignored_jump_destination_preserves_local_flow_without_linking():
    target = BASE + 0x10
    debugger = configured_debugger(
        f"jal 0x{target:X}", "addiu $t0, $zero, 3", "nop", "nop", "nop", ignored=(target,)
    )

    debugger.step()

    assert debugger.pc == BASE + 4
    assert debugger.registers.read("ra") == 0
    assert debugger.statistics.ignored[target] == 1
    assert any("reached" in event.details for event in debugger.events)


def test_ignored_direct_jump_destination_advances_locally():
    target = BASE + 0x10
    debugger = configured_debugger(f"j 0x{target:X}", "nop", "nop", "nop", "nop", ignored=(target,))

    debugger.step()

    assert debugger.pc == BASE + 4
    assert debugger.statistics.ignored[target] == 1


def test_ignored_jalr_destination_does_not_change_return_address():
    target = BASE + 0x10
    debugger = configured_debugger(
        f"addiu $t0, $zero, 0x{target:X}",
        "jalr $ra, $t0",
        "nop",
        "nop",
        "nop",
        ignored=(target,),
    )
    debugger.step()

    debugger.step()

    assert debugger.pc == BASE + 8
    assert debugger.registers.read("ra") == 0
    assert debugger.statistics.ignored[target] == 1


def test_memory_hooks_capture_load_store_context_and_restart_clears_statistics():
    debugger = configured_debugger(
        "addiu $t0, $zero, 0x1100",
        "addiu $t1, $zero, 0x1234",
        "sw $t1, 0($t0)",
        "lw $t2, 0($t0)",
        "nop",
    )

    for _ in range(5):
        debugger.step()

    assert debugger.statistics.writes[0x1100] == 1
    assert debugger.statistics.reads[0x1100] == 1
    memory_events = [event for event in debugger.events if event.level == "Memory"]
    assert {event.details["size"] for event in memory_events} == {4}
    assert {event.details["value"] for event in memory_events} == {0x1234}
    assert all("pc" in event.details and "instruction" in event.details for event in memory_events)
    debugger.restart()

    assert debugger.state == DebuggerSessionState.READY
    assert debugger.statistics.reads == {}
    assert debugger.statistics.writes == {}


def test_execution_limit_leaves_session_available_to_continue():
    debugger = configured_debugger(f"j 0x{BASE:X}", "nop")

    debugger.run(limit=3)

    assert debugger.state == DebuggerSessionState.PAUSED
    assert any("safety limit" in event.message for event in debugger.events)
    debugger.run(limit=1)
    assert debugger.state == DebuggerSessionState.PAUSED


def test_unaligned_access_is_logged_with_its_effective_address():
    debugger = configured_debugger(
        "addiu $t0, $zero, 0x1101",
        "lw $t1, 0($t0)",
        "nop",
    )
    debugger.step()

    with pytest.raises(DebuggerError):
        debugger.step()

    event = next(item for item in debugger.events if item.level == "Alignment Memory Error")
    assert event.address == 0x1101
    assert event.details["pc"] == BASE + 4
