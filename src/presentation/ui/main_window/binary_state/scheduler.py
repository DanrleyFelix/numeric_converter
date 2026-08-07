from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal

from src.modules.binary_workbench_dtos import BinaryWorkbenchStateDTO


@dataclass(frozen=True)
class BinaryStatePersistenceResult:
    """Describe one coalesced Binary session-state write."""

    revision: int
    path: object | None = None
    error: str | None = None


class _PersistenceSignals(QObject):
    completed = Signal(object)


class _PersistenceWorker(QRunnable):
    """Serialize a Binary state snapshot away from the GUI thread."""

    def __init__(
        self,
        state: BinaryWorkbenchStateDTO,
        revision: int,
        persist: Callable[[BinaryWorkbenchStateDTO], object],
    ) -> None:
        super().__init__()
        self._state = state
        self._revision = revision
        self._persist = persist
        self.result: BinaryStatePersistenceResult | None = None
        self.signals = _PersistenceSignals()

    def run(self) -> None:
        """Persist the captured immutable DTO and retain the result for close."""

        try:
            path = self._persist(self._state)
            self.result = BinaryStatePersistenceResult(self._revision, path=path)
        except PermissionError:
            self.result = BinaryStatePersistenceResult(self._revision)
        except Exception as error:
            self.result = BinaryStatePersistenceResult(
                self._revision,
                error=str(error),
            )
        self.signals.completed.emit(self.result)


class BinaryStatePersistenceScheduler(QObject):
    """Coalesce large Binary state writes without blocking editor actions."""

    def __init__(
        self,
        persist: Callable[[BinaryWorkbenchStateDTO], object],
        parent: QObject,
        debounce_ms: int = 3_000,
    ) -> None:
        super().__init__(parent)
        self._persist = persist
        self._revision = 0
        self._pending_state: BinaryWorkbenchStateDTO | None = None
        self._in_flight = False
        self._worker: _PersistenceWorker | None = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(debounce_ms)
        self._timer.timeout.connect(self.flush_due)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)

    def schedule(self, state: BinaryWorkbenchStateDTO) -> None:
        """Keep only the newest state emitted by a burst of Binary events."""

        self._revision += 1
        self._pending_state = state
        if not self._in_flight:
            self._timer.start()

    def flush_due(self) -> None:
        """Start at most one Binary persistence worker."""

        self._timer.stop()
        if self._in_flight or self._pending_state is None:
            return
        state = self._pending_state
        revision = self._revision
        self._pending_state = None
        self._in_flight = True
        worker = _PersistenceWorker(state, revision, self._persist)
        self._worker = worker
        worker.signals.completed.connect(self._handle_completed)
        self._pool.start(worker)

    def flush_on_close(self) -> BinaryStatePersistenceResult:
        """Join an active write and persist the newest pending state once."""

        self._timer.stop()
        if self._in_flight:
            if not self._pool.waitForDone(5_000):
                return BinaryStatePersistenceResult(
                    self._revision,
                    error="Binary state persistence did not finish before close.",
                )
            worker = self._worker
            if worker is not None and worker.result is not None:
                try:
                    worker.signals.completed.disconnect(self._handle_completed)
                except (RuntimeError, TypeError):
                    pass
                self._handle_completed(worker.result)
        if self._pending_state is None:
            return BinaryStatePersistenceResult(self._revision)
        state = self._pending_state
        revision = self._revision
        self._pending_state = None
        try:
            path = self._persist(state)
            return BinaryStatePersistenceResult(revision, path=path)
        except PermissionError:
            return BinaryStatePersistenceResult(revision)
        except Exception as error:
            return BinaryStatePersistenceResult(revision, error=str(error))

    def shutdown(self) -> None:
        """Stop work owned only by Binary session-state persistence."""

        self._timer.stop()
        self._pool.clear()
        self._pool.waitForDone(1_000)
        self._worker = None

    def _handle_completed(self, result: BinaryStatePersistenceResult) -> None:
        """Continue only when a newer coalesced state is waiting."""

        self._in_flight = False
        self._worker = None
        if self._pending_state is not None:
            self._timer.start()
