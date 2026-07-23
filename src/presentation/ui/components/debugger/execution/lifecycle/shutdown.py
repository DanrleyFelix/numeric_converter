from __future__ import annotations

from src.core.debugger.contracts.base import BWDebugger
from src.presentation.ui.components.debugger.execution.worker import DebuggerExecutionWorker


def stop_execution_worker(
    debugger: BWDebugger,
    worker: DebuggerExecutionWorker | None,
) -> bool:
    """Cooperatively stop a worker across its startup race window."""

    if worker is None or not worker.isRunning():
        return True
    debugger.stop()
    if worker.wait(100):
        return True
    debugger.stop()
    return worker.wait(2900)
