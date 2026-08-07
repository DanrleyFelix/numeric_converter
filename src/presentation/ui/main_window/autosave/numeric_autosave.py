from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal

from src.modules.application_dtos import ApplicationContextDTO


@dataclass(frozen=True)
class NumericAutosaveResult:
    """Describe one isolated Numeric context persistence result."""

    revision: object
    path: object
    dirty_revisions: tuple[tuple[str, object], ...] = ()


@dataclass(frozen=True)
class PersistenceResult:
    """Report the exclusive Numeric close barrier without raising into Qt."""

    success: bool
    path: object | None = None
    error: str | None = None


class _AutosaveSignals(QObject):
    saved = Signal(object)
    failed = Signal(str)


class _AutosaveWorker(QRunnable):
    """Persist a Numeric-only immutable snapshot outside the UI thread."""

    def __init__(
        self,
        context: ApplicationContextDTO,
        revision: object,
        persist: Callable[[ApplicationContextDTO], object],
        dirty_revisions: tuple[tuple[str, object], ...],
    ) -> None:
        super().__init__()
        self._context = context
        self._revision = revision
        self._persist = persist
        self._dirty_revisions = dirty_revisions
        self.result: NumericAutosaveResult | None = None
        self.error: str | None = None
        self.signals = _AutosaveSignals()

    def run(self) -> None:
        """Write the captured context without touching another workbench."""

        try:
            path = self._persist(self._context)
            self.result = NumericAutosaveResult(
                self._revision,
                path,
                self._dirty_revisions,
            )
            self.signals.saved.emit(self.result)
        except Exception as error:
            self.error = str(error)
            self.signals.failed.emit(self.error)


class NumericAutosaveScheduler(QObject):
    """Rate-limit Numeric persistence without reacting to every keystroke."""

    saved = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        snapshot_provider: Callable[[], tuple[ApplicationContextDTO, object]],
        revision_provider: Callable[[], object],
        persist: Callable[[ApplicationContextDTO], object],
        interval_ms: int,
        parent: QObject,
    ) -> None:
        super().__init__(parent)
        self._snapshot_provider = snapshot_provider
        self._revision_provider = revision_provider
        self._persist = persist
        self._interval_ms = interval_ms
        self._pending = False
        self._dirty_revisions: dict[str, object] = {}
        self._in_flight = False
        self._last_saved_revision: object | None = None
        self._worker: _AutosaveWorker | None = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.flush_due)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)

    def mark_dirty(self, kind: str, revision: object) -> None:
        """Record one logical Numeric change and arm one stable timer."""

        self._pending = True
        self._dirty_revisions[kind] = revision
        if not self._timer.isActive() and not self._in_flight:
            self._timer.start(self._interval_ms)

    def flush_due(self) -> None:
        """Capture the latest Numeric revision only when the timer is due."""

        self._timer.stop()
        if not self._pending or self._in_flight:
            return
        context, revision = self._snapshot_provider()
        self._pending = False
        self._in_flight = True
        dirty_revisions = tuple(self._dirty_revisions.items())
        worker = _AutosaveWorker(context, revision, self._persist, dirty_revisions)
        self._worker = worker
        worker.signals.saved.connect(self._handle_saved)
        worker.signals.failed.connect(self._handle_failed)
        self._pool.start(worker)

    def flush_on_close(self) -> PersistenceResult:
        """Persist pending Numeric state synchronously during close."""

        self._timer.stop()
        if self._in_flight:
            if not self._pool.waitForDone(2_000):
                return PersistenceResult(
                    False,
                    error="Numeric autosave did not finish before close.",
                )
            worker = self._worker
            if worker is not None and worker.result is not None:
                try:
                    worker.signals.saved.disconnect(self._handle_saved)
                except (RuntimeError, TypeError):
                    pass
                self._handle_saved(worker.result)
            elif worker is not None and worker.error is not None:
                return PersistenceResult(False, error=worker.error)
        if not self._pending and not self._dirty_revisions:
            return PersistenceResult(True)
        try:
            context, revision = self._snapshot_provider()
            path = self._persist(context)
        except Exception as error:
            return PersistenceResult(False, error=str(error))
        self._pending = False
        self._dirty_revisions.clear()
        self._last_saved_revision = revision
        return PersistenceResult(True, path=path)

    def shutdown(self) -> None:
        """Stop only Numeric autosave work owned by this scheduler."""

        self._timer.stop()
        self._pool.clear()
        self._pool.waitForDone(1_000)
        self._worker = None

    def _handle_saved(self, result: NumericAutosaveResult) -> None:
        """Accept a save only when no newer Numeric state replaced it."""

        self._in_flight = False
        self._worker = None
        if result.revision == self._revision_provider():
            self._last_saved_revision = result.revision
            for kind, revision in result.dirty_revisions:
                if self._dirty_revisions.get(kind) == revision:
                    self._dirty_revisions.pop(kind, None)
            self.saved.emit(result)
        else:
            self._pending = True
        self._pending = bool(self._dirty_revisions) or self._pending
        if self._pending:
            self._timer.start(self._interval_ms)

    def _handle_failed(self, message: str) -> None:
        """Keep failed work pending and report it without blocking input."""

        self._in_flight = False
        self._worker = None
        self._pending = True
        self.failed.emit(message)
        self._timer.start(self._interval_ms)
