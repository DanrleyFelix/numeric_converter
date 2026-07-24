from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMainWindow

from src.core.debugger.models.session import DebuggerSessionState
from src.core.debugger.session.factory import DebuggerSessionBundle
from src.presentation.repository.debugger_window.repository import DebuggerWindowStateRepository
from src.presentation.ui.components.debugger.actions import DebuggerActions
from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT
from src.presentation.ui.components.debugger.constants.texts import (
    DEBUGGER_TITLE,
    DEBUGGER_WORKER_STOP_ERROR,
)
from src.presentation.ui.components.debugger.execution.control.window import (
    DebuggerWindowControlMixin,
)
from src.presentation.ui.components.debugger.execution.worker import DebuggerExecutionWorker
from src.presentation.ui.components.debugger.execution.status import latest_execution_address
from src.presentation.ui.components.debugger.execution.lifecycle.shutdown import stop_execution_worker
from src.presentation.ui.components.debugger.shell.layout import build_debugger_shell
from src.presentation.ui.components.debugger.shell.persistence import restore_debugger_window, save_debugger_window
from src.presentation.ui.helpers.load_qss import STYLESHEET

class DebuggerWindow(DebuggerWindowControlMixin, QMainWindow):
    """Present and control one isolated debugger session."""

    statusError = Signal(str)

    def __init__(
        self,
        bundle: DebuggerSessionBundle,
        actions: DebuggerActions,
        repository: DebuggerWindowStateRepository,
        workspace_key: str,
        parent=None,
    ) -> None:
        """Create a persisted window around a complete validated session."""
        super().__init__(parent)
        self.bundle = bundle
        self.debugger = bundle.debugger
        self.actions = actions
        self._repository = repository
        self._workspace_key = workspace_key
        self._worker: DebuggerExecutionWorker | None = None
        self._last_pc: int | None = None
        self.setObjectName("debugger-window")
        self.setWindowTitle(f"{DEBUGGER_TITLE} — {workspace_key}")
        self.setMinimumSize(DEBUGGER_LAYOUT.MIN_WIDTH, DEBUGGER_LAYOUT.MIN_HEIGHT)
        self.setStyleSheet(STYLESHEET)
        shell, self.panels = build_debugger_shell(self, bundle, actions)
        self.setCentralWidget(shell)
        self.addActions(list(actions.all()))
        self.panels.instructions.breakpointToggled.connect(self._toggle_breakpoint)
        self.panels.instructions.breakpointRemoved.connect(self._remove_breakpoint)
        self.panels.instructions.ignoredToggled.connect(self._toggle_ignored)
        self.panels.lower.navigateRequested.connect(self.panels.instructions.navigate_to)
        self.panels.lower.memory.errorRaised.connect(self.statusError.emit)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(150)
        self._refresh_timer.timeout.connect(self.refresh)
        restore_debugger_window(self, repository, workspace_key)
        self.refresh()

    def refresh(self) -> None:
        """Refresh every view from the latest isolated session state."""
        latest = latest_execution_address(self.debugger)
        if latest is not None:
            self._last_pc = latest
        self.panels.instructions.refresh(self.debugger, self._last_pc)
        self.panels.registers.refresh()
        if self.debugger.state == DebuggerSessionState.RUNNING:
            self.panels.lower.refresh_running()
        else:
            self.panels.lower.refresh()

    def _toggle_breakpoint(self, address: int) -> None:
        """Toggle breakpoint metadata from the instruction gutter."""
        self.debugger.toggle_breakpoint(address)
        self.refresh()

    def _toggle_ignored(self, address: int) -> None:
        """Toggle an explicit IGNORED instruction and refresh its status."""
        self.debugger.toggle_ignored_instruction(address)
        self.refresh()

    def _remove_breakpoint(self, address: int) -> None:
        """Remove breakpoint metadata requested by the instruction menu."""

        self.debugger.remove_breakpoint(address)
        self.refresh()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Persist layout and safely finish execution before closing."""
        if not stop_execution_worker(self.debugger, self._worker):
            self.statusError.emit(DEBUGGER_WORKER_STOP_ERROR)
            event.ignore()
            return
        self.debugger.record_event("Info", "Debugger session closed.")
        save_debugger_window(self, self._repository, self._workspace_key)
        super().closeEvent(event)
