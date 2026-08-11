"""Regression coverage for the packaged native Debugger smoke scenario."""

from src.core.debugger.models.session import DebuggerSessionState
from src.core.debugger.runtime_smoke import (
    SMOKE_EXECUTION_LIMIT,
    SMOKE_EXPECTED_V0,
    SMOKE_FINAL_PC,
    create_debugger_native_smoke_session,
    run_debugger_native_smoke,
    validate_debugger_native_smoke,
)
from src.presentation.ui.components.debugger.execution.worker import (
    DebuggerExecutionWorker,
)


def test_native_smoke_executes_jal_delay_slot_and_return_in_core():
    """Require the exact reported JAL program to finish with valid state."""

    result = run_debugger_native_smoke()

    assert result.pc == SMOKE_FINAL_PC
    assert result.v0 == SMOKE_EXPECTED_V0
    assert result.state == DebuggerSessionState.STOPPED
    assert result.error is None


def test_native_smoke_executes_through_debugger_qthread_worker():
    """Require the window's F5 worker path to preserve native execution."""

    debugger = create_debugger_native_smoke_session()
    worker = DebuggerExecutionWorker(
        lambda: debugger.run(limit=SMOKE_EXECUTION_LIMIT)
    )

    worker.start()
    assert worker.wait(5_000)

    result = validate_debugger_native_smoke(debugger)
    assert result.pc == SMOKE_FINAL_PC
    assert result.v0 == SMOKE_EXPECTED_V0
