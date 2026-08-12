from threading import Thread
from time import monotonic, sleep

import pytest

from src.core.debugger.models.session import (
    DebuggerError,
    DebuggerInstruction,
    DebuggerSessionState,
)
from src.presentation.ui.components.debugger.execution.control.window import (
    DebuggerWindowControlMixin,
)
from helpers import BASE, END, configured_debugger


def test_run_stops_before_an_enabled_breakpoint():
    debugger = configured_debugger("addiu $t0, $zero, 1", "addiu $t1, $zero, 2")
    debugger.add_breakpoint(BASE + 4)

    debugger.run(limit=10)

    assert debugger.state == DebuggerSessionState.PAUSED
    assert debugger.pc == BASE + 4
    assert debugger.registers.read("t0") == 1
    assert debugger.registers.read("t1") == 0

    debugger.run(limit=1)

    assert debugger.registers.read("t1") == 2


def test_breakpoint_name_survives_state_changes_and_restart():
    """Retain one validated display name with breakpoint metadata."""

    debugger = configured_debugger("nop", "nop")
    debugger.add_breakpoint(BASE + 4, name="loop_exit")
    debugger.set_breakpoint_enabled(BASE + 4, False)
    assert debugger.breakpoints[0].name == "loop_exit"
    debugger.restart()
    assert debugger.breakpoints[0].name == "loop_exit"


def test_execution_interval_is_retained_and_applied():
    """Expose configured pacing while preserving zero as the fastest mode."""

    debugger = configured_debugger("nop", "nop")
    debugger.set_execution_interval(1)

    debugger.run(limit=1)

    assert debugger.execution_interval_ms == 1
    assert debugger.state == DebuggerSessionState.PAUSED


def test_window_run_restarts_a_stopped_session_before_execution():
    """Make F5 create a valid execution state after Stop."""

    class StoppedDebugger:
        state = DebuggerSessionState.STOPPED

        def __init__(self):
            self.restart_count = 0

        def restart(self):
            self.restart_count += 1
            self.state = DebuggerSessionState.READY

        def run(self):
            return None

    class Control(DebuggerWindowControlMixin):
        def __init__(self):
            self.debugger = StoppedDebugger()
            self._last_pc = 1
            self._worker = None
            self.operation = None

        def _start_worker(self, operation):
            self.operation = operation

    control = Control()
    control._run()

    assert control.debugger.restart_count == 1
    assert control._last_pc is None
    assert control.operation == control.debugger.run


def test_window_run_does_not_restart_a_ready_session():
    """Keep manually prepared registers when F5 starts from Ready."""

    class ReadyDebugger:
        state = DebuggerSessionState.READY

        def __init__(self):
            self.restart_count = 0

        def restart(self):
            self.restart_count += 1

        def run(self):
            return None

    class Control(DebuggerWindowControlMixin):
        def __init__(self):
            self.debugger = ReadyDebugger()
            self._last_pc = None
            self._worker = None
            self.operation = None

        def _start_worker(self, operation):
            self.operation = operation

    control = Control()
    control._run()

    assert control.debugger.restart_count == 0
    assert control.operation == control.debugger.run


def test_restart_restores_directives_and_discards_manual_register_edits():
    """Use directives and zero defaults as the sole Restart baseline."""

    debugger = configured_debugger(
        "nop",
        register_values={"gp": 0x12345678, "a0": 7},
    )
    debugger.registers.write("gp", 1)
    debugger.registers.write("a0", 2)
    debugger.registers.write("t0", 3)
    debugger.registers.write("zero", 4)

    debugger.restart()

    assert debugger.state == DebuggerSessionState.READY
    assert debugger.pc == BASE
    assert debugger.registers.read("sp") == END - 3
    assert debugger.registers.read("gp") == 0x12345678
    assert debugger.registers.read("a0") == 7
    assert debugger.registers.read("t0") == 0
    assert debugger.registers.read("zero") == 0


def test_step_uses_registers_and_pc_edited_after_restart():
    """Execute directly from the user-prepared Ready register snapshot."""

    debugger = configured_debugger(
        "addiu $t0, $zero, 1",
        "addu $v0, $a0, $a1",
        "nop",
    )
    debugger.restart()
    debugger.pc = BASE + 4
    debugger.registers.write("a0", 20)
    debugger.registers.write("a1", 22)

    debugger.step()

    assert debugger.registers.read("v0") == 42
    assert debugger.registers.read("t0") == 0
    assert debugger.pc == BASE + 8


def test_run_preserves_ready_register_edits_without_an_implicit_restart():
    """Continue F5 from Ready without restoring directive values again."""

    debugger = configured_debugger("addu $v0, $a0, $a1", "nop")
    debugger.restart()
    debugger.registers.write("a0", 9)
    debugger.registers.write("a1", 4)

    debugger.run(limit=1)

    assert debugger.registers.read("v0") == 13
    assert debugger.state == DebuggerSessionState.PAUSED


def test_continue_preserves_register_edits_made_while_paused():
    """Synchronize a Paused edit before continuing with F5."""

    debugger = configured_debugger(
        "addiu $t0, $zero, 1",
        "addu $v0, $a0, $t0",
        "nop",
    )
    debugger.run(limit=1)
    debugger.registers.write("a0", 41)

    debugger.run(limit=1)

    assert debugger.registers.read("v0") == 42
    assert debugger.state == DebuggerSessionState.PAUSED


def test_step_over_preserves_register_edits_after_restart():
    """Carry the prepared register state through a complete local call."""

    debugger = configured_debugger(
        f"jal 0x{BASE + 0x10:X}",
        "nop",
        "nop",
        "nop",
        "addiu $v0, $a0, 5",
        "jr $ra",
        "nop",
    )
    debugger.restart()
    debugger.registers.write("a0", 37)

    debugger.step_over(limit=20)

    assert debugger.registers.read("v0") == 42
    assert debugger.pc == BASE + 8


def test_invalid_edited_pc_is_reported_as_a_controlled_error():
    """Retain an invalid manual PC as an Error event instead of crashing."""

    debugger = configured_debugger("nop")
    debugger.restart()
    debugger.pc = BASE + 0x100

    debugger.run(limit=1)

    assert debugger.state == DebuggerSessionState.ERROR
    assert debugger.last_error is not None
    assert debugger.events[-1].level == "Error"
    assert f"PC 0x{BASE + 0x100:08X}" in debugger.events[-1].message


def test_step_over_runs_jal_until_its_return_address():
    debugger = configured_debugger(
        f"jal 0x{BASE + 0x10:X}",
        "nop",
        "addiu $t0, $zero, 7",
        "nop",
        "addiu $v0, $zero, 5",
        "jr $ra",
        "nop",
    )

    debugger.step_over(limit=20)

    assert debugger.state == DebuggerSessionState.PAUSED
    assert debugger.pc == BASE + 8
    assert debugger.registers.read("v0") == 5
    assert debugger.registers.read("t0") == 0


def test_step_over_honors_breakpoint_inside_call():
    debugger = configured_debugger(
        f"jal 0x{BASE + 0x10:X}", "nop", "nop", "nop", "nop", "jr $ra", "nop"
    )
    debugger.add_breakpoint(BASE + 0x10)

    debugger.step_over(limit=20)

    assert debugger.pc == BASE + 0x10
    assert debugger.state == DebuggerSessionState.PAUSED


def test_step_and_run_finish_cleanly_after_the_last_instruction():
    """Treat the address immediately after the loaded image as normal completion."""

    for execute in (lambda debugger: debugger.step(), lambda debugger: debugger.run(limit=2)):
        debugger = configured_debugger("nop")

        execute(debugger)

        assert debugger.pc == BASE + 4
        assert debugger.state == DebuggerSessionState.STOPPED
        assert not any(event.level == "Error" for event in debugger.events)
        assert debugger.events[-1].message == f"Execution completed at 0x{BASE + 4:08X}."


def test_run_reports_an_unloaded_call_destination_without_escaping():
    """Keep an invalid JAL target inside the Debug Log and debugger state."""

    target = BASE + 0x100
    debugger = configured_debugger(f"jal 0x{target:X}", "nop")

    debugger.run(limit=3)

    assert debugger.state == DebuggerSessionState.ERROR
    assert debugger.pc == target
    assert debugger.last_error is not None
    assert f"PC 0x{target:08X}" in debugger.last_error.message
    assert "JAL/JALR" in debugger.last_error.message
    assert "IGNORED" in debugger.last_error.message
    assert debugger.events[-1].level == "Error"
    assert debugger.events[-1].message == debugger.last_error.message


def test_pause_and_stop_are_cooperative_and_restart_restores_state():
    debugger = configured_debugger(f"j 0x{BASE:X}", "nop")
    worker = Thread(target=lambda: debugger.run(limit=10_000_000))
    worker.start()
    deadline = monotonic() + 2
    while debugger.state != DebuggerSessionState.RUNNING and monotonic() < deadline:
        sleep(0.001)
    debugger.pause()
    worker.join(2)

    assert not worker.is_alive()
    assert debugger.state == DebuggerSessionState.PAUSED
    debugger.add_breakpoint(BASE)
    debugger.toggle_ignored_instruction(BASE + 4)
    debugger.write_memory(BASE, b"\0\0\0\0")
    debugger.stop()
    with pytest.raises(DebuggerError):
        debugger.run(limit=1)
    debugger.restart()

    assert debugger.state == DebuggerSessionState.READY
    assert debugger.read_memory(BASE, 4) != b"\0\0\0\0"
    assert debugger.breakpoints[0].address == BASE
    assert BASE + 4 in debugger.ignored_instructions
