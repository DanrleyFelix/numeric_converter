from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from src.core.binary_workbench.editor_consistency.cancellation import CancellationToken
from src.core.binary_workbench.editor_consistency.models import SemanticSnapshot
from src.core.binary_workbench.editor_consistency.semantic import (
    calculate_derived_copy_result,
)

# No eventual maintenance is submitted to this pool.  Its single worker is
# reserved for an explicit broad-copy request, so ordinary editing, dialogs
# and toolbar repainting never compete with a background Assembly batch.
EDITOR_CONSISTENCY_WORKERS = 1
IMMEDIATE_WORK_PRIORITY = 2


class ConsistencyWorkerSignals(QObject):
    """Deliver immutable worker results back to the Qt main thread."""

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


class DerivedCopyWorker(QRunnable):
    """Prepare broad copy rows without diagnostics or Qt projection work."""

    def __init__(self, snapshot: SemanticSnapshot, token: CancellationToken) -> None:
        super().__init__()
        self.snapshot = snapshot
        self.token = token
        self.signals = ConsistencyWorkerSignals()

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

    def start_immediate(self, worker: DerivedCopyWorker) -> None:
        """Start an explicit user request ahead of eventual maintenance."""

        self.pool.start(worker, IMMEDIATE_WORK_PRIORITY)

    def clear(self) -> None:
        """Remove workers that have not begun without terminating threads."""

        self.pool.clear()

    def shutdown(self, timeout_ms: int = 50) -> None:
        """Cancel queued work and let active cooperative workers leave safely."""

        self.pool.clear()
        self.pool.waitForDone(timeout_ms)
