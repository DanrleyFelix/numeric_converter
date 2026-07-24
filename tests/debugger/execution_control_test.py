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
from helpers import BASE, configured_debugger


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
            self.restarted = False

        def restart(self):
            self.restarted = True
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

    assert control.debugger.restarted
    assert control._last_pc is None
    assert control.operation == control.debugger.run


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
