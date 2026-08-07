from __future__ import annotations

from threading import Event

from PySide6.QtCore import QObject, QRunnable, QThread, QThreadPool, Signal

from src.core.binary_workbench.editor_consistency.cancellation import CancellationToken
from src.core.binary_workbench.editor_consistency.distribution import iter_offset_batches
from src.core.binary_workbench.editor_consistency.models import SemanticSnapshot
from src.core.binary_workbench.editor_consistency.semantic import (
    calculate_derived_copy_result,
    calculate_semantic_result,
)

# One CPU-bound worker leaves the majority of a modest four-core machine for
# direct editing, navigation and painting. User work still outranks eventual
# maintenance inside this bounded queue.
EDITOR_CONSISTENCY_WORKERS = 1
VISUAL_WORK_PRIORITY = 1
SEMANTIC_WORK_PRIORITY = 0
IMMEDIATE_WORK_PRIORITY = 2


class ConsistencyWorkerSignals(QObject):
    """Deliver immutable worker results back to the Qt main thread."""

    offsetBatchReady = Signal(object)
    semanticReady = Signal(object)
    failed = Signal(str)
    completed = Signal(object)


def _safe_emit(signal, *values) -> bool:
    """Ignore delivery after the owning editor has already been destroyed."""

    try:
        signal.emit(*values)
    except RuntimeError:
        return False
    return True


class OffsetDistributionWorker(QRunnable):
    """Calculate prioritized File and Reference Offset batches."""

    def __init__(self, request: dict, token: CancellationToken) -> None:
        super().__init__()
        self.request = request
        self.token = token
        self.signals = ConsistencyWorkerSignals()
        self._batch_applied = Event()

    def acknowledge_batch(self) -> None:
        """Release the worker after the UI accepts or rejects one batch."""

        self._batch_applied.set()

    def run(self) -> None:
        """Emit each valid batch and one completion envelope."""

        try:
            for batch in iter_offset_batches(token=self.token, **self.request):
                if self.token.is_cancelled():
                    return
                self._batch_applied.clear()
                if not _safe_emit(self.signals.offsetBatchReady, batch):
                    return
                # Direct test execution runs on the signal object's thread.
                # The real pool path waits cooperatively, bounding the UI queue
                # to one ready batch without ever terminating a thread.
                if QThread.currentThread() is not self.signals.thread():
                    while not self._batch_applied.wait(0.02):
                        if self.token.is_cancelled():
                            return
            if not self.token.is_cancelled():
                _safe_emit(
                    self.signals.completed,
                    (
                        self.request["owner"],
                        self.request["structural_revision"],
                        self.request["generation"],
                    )
                )
        except Exception as error:
            _safe_emit(self.signals.failed, str(error))


class SemanticWorker(QRunnable):
    """Calculate one complete semantic result away from Qt documents."""

    def __init__(self, snapshot: SemanticSnapshot, token: CancellationToken) -> None:
        super().__init__()
        self.snapshot = snapshot
        self.token = token
        self.signals = ConsistencyWorkerSignals()

    def run(self) -> None:
        """Emit only a complete current semantic calculation."""

        try:
            result = calculate_semantic_result(self.snapshot, self.token)
            if result is not None and not self.token.is_cancelled():
                _safe_emit(self.signals.semanticReady, result)
        except Exception as error:
            _safe_emit(self.signals.failed, str(error))


class DerivedCopyWorker(SemanticWorker):
    """Prepare broad copy rows without diagnostics or Qt projection work."""

    def run(self) -> None:
        """Emit only copy-relevant rows for the immutable source snapshot."""

        try:
            result = calculate_derived_copy_result(self.snapshot, self.token)
            if result is not None and not self.token.is_cancelled():
                _safe_emit(self.signals.semanticReady, result)
        except Exception as error:
            _safe_emit(self.signals.failed, str(error))


class EditorConsistencyWorkerPool:
    """Own the bounded worker pool used by one editor grid."""

    def __init__(self, parent: QObject) -> None:
        self.pool = QThreadPool(parent)
        self.pool.setMaxThreadCount(EDITOR_CONSISTENCY_WORKERS)

    def start_visual(self, worker: OffsetDistributionWorker) -> None:
        """Start visual work ahead of queued semantic work."""

        self.pool.start(worker, VISUAL_WORK_PRIORITY)

    def start_semantic(self, worker: SemanticWorker) -> None:
        """Start lower-priority semantic work."""

        self.pool.start(worker, SEMANTIC_WORK_PRIORITY)

    def start_immediate(self, worker: SemanticWorker) -> None:
        """Start an explicit user request ahead of eventual maintenance."""

        self.pool.start(worker, IMMEDIATE_WORK_PRIORITY)

    def clear(self) -> None:
        """Remove workers that have not begun without terminating threads."""

        self.pool.clear()

    def shutdown(self, timeout_ms: int = 1000) -> None:
        """Cancel queued work and let active cooperative workers leave safely."""

        self.pool.clear()
        self.pool.waitForDone(timeout_ms)
