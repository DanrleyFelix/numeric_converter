from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QThread, Signal


class DebuggerExecutionWorker(QThread):
    """Run one debugger operation outside the interface thread."""

    completed = Signal()
    failed = Signal(str)

    def __init__(self, operation: Callable[[], None], parent=None) -> None:
        """Store one bounded execution callback for the worker thread."""

        super().__init__(parent)
        self._operation = operation

    def run(self) -> None:
        """Execute the operation and publish controlled completion state."""

        try:
            self._operation()
        except Exception as error:
            self.failed.emit(str(error))
            return
        self.completed.emit()
