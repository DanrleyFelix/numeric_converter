"""Debugger-window execution command handling."""

from src.core.debugger.models.session import DebuggerError, DebuggerSessionState
from src.presentation.ui.components.debugger.config.dialog import (
    ask_debugger_config,
)
from src.presentation.ui.components.debugger.constants.texts import (
    DEBUGGER_WORKER_STOP_ERROR,
)
from src.presentation.ui.components.debugger.execution.lifecycle.shutdown import (
    stop_execution_worker,
)
from src.presentation.ui.components.debugger.execution.worker import (
    DebuggerExecutionWorker,
)


class DebuggerWindowControlMixin:
    """Route toolbar operations without mixing them with window assembly."""

    def perform(self, operation: str) -> None:
        """Dispatch one shared QAction to the current debugger session."""

        handlers = {
            "run": self._run,
            "pause": self._pause,
            "stop": self._stop,
            "restart": self._restart,
            "step": self._step,
            "step_over": lambda: self._start_worker(self.debugger.step_over),
            "config": self._config,
        }
        handler = handlers.get(operation)
        if handler is not None:
            handler()

    def _run(self) -> None:
        """Restart a stopped session or continue a ready/paused one."""

        if self.debugger.state == DebuggerSessionState.STOPPED:
            if not stop_execution_worker(self.debugger, self._worker):
                self.statusError.emit(DEBUGGER_WORKER_STOP_ERROR)
                return
            self.debugger.restart()
            self._last_pc = None
        self._start_worker(self.debugger.run)

    def _start_worker(self, operation) -> None:
        """Start one continuous operation without blocking Qt."""

        if self._worker is not None and self._worker.isRunning():
            return
        self._last_pc = self.debugger.pc
        self._worker = DebuggerExecutionWorker(operation, self)
        self._worker.completed.connect(self._worker_finished)
        self._worker.failed.connect(self._worker_failed)
        worker = self._worker
        self._worker.finished.connect(
            lambda: setattr(self, "_worker", None) if self._worker is worker else None
        )
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()
        self._refresh_timer.start()

    def _worker_finished(self) -> None:
        """Stop periodic updates and render the final execution state."""

        self._refresh_timer.stop()
        self.refresh()

    def _worker_failed(self, message: str) -> None:
        """Expose a controlled execution failure without crashing."""

        self._refresh_timer.stop()
        self.statusError.emit(message)
        self.refresh()

    def _step(self) -> None:
        """Execute one synchronous bounded step and refresh immediately."""

        self._last_pc = self.debugger.pc
        try:
            self.debugger.step()
        except DebuggerError as error:
            self.statusError.emit(error.message)
        self.refresh()

    def _pause(self) -> None:
        """Request a cooperative Pause on the active worker."""

        try:
            self.debugger.pause()
        except DebuggerError as error:
            self.statusError.emit(error.message)

    def _stop(self) -> None:
        """Invalidate the current session until Run or Restart."""

        self.debugger.stop()
        self.refresh()

    def _restart(self) -> None:
        """Restore the immutable initial session snapshot."""

        if not stop_execution_worker(self.debugger, self._worker):
            self.statusError.emit(DEBUGGER_WORKER_STOP_ERROR)
            return
        self.debugger.restart()
        self._last_pc = None
        self.refresh()

    def _config(self) -> None:
        """Apply a confirmed automatic execution interval."""

        config = ask_debugger_config(
            self,
            self.panels.lower.log.enabled_levels,
        )
        if config is not None:
            interval, enabled_levels = config
            self.debugger.set_execution_interval(interval)
            self.panels.lower.log.set_enabled_levels(enabled_levels)
            self.refresh()
