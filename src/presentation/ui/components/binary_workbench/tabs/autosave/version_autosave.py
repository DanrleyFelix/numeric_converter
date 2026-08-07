from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal

from src.modules.binary_workbench_dtos import BinaryWorkbenchTabContextDTO
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_TIMING,
)


@dataclass(frozen=True)
class VersionAutosaveResult:
    """Describe one completed active-version-only persistence job."""

    tab_id: str
    generation: int
    module_paths: dict[str, str]


class _VersionAutosaveSignals(QObject):
    saved = Signal(object)
    failed = Signal(str)


class _VersionAutosaveWorker(QRunnable):
    """Persist one immutable tab snapshot outside the Qt main thread."""

    def __init__(
        self,
        tab_id: str,
        generation: int,
        snapshot: BinaryWorkbenchTabContextDTO,
        persist: Callable[[BinaryWorkbenchTabContextDTO], dict[str, str]],
    ) -> None:
        super().__init__()
        self._tab_id = tab_id
        self._generation = generation
        self._snapshot = snapshot
        self._persist = persist
        self.signals = _VersionAutosaveSignals()

    def run(self) -> None:
        """Write only the active version and report its module paths."""

        try:
            paths = self._persist(self._snapshot)
            self.signals.saved.emit(
                VersionAutosaveResult(
                    self._tab_id,
                    self._generation,
                    paths,
                )
            )
        except Exception as error:
            self.signals.failed.emit(str(error))


class VersionAutosaveScheduler(QObject):
    """Debounce Assembly snapshots and rate-limit each tab's persistence."""

    saved = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        snapshot_provider: Callable[[str], BinaryWorkbenchTabContextDTO | None],
        persist: Callable[[BinaryWorkbenchTabContextDTO], dict[str, str]],
        parent: QObject,
    ) -> None:
        super().__init__(parent)
        self._snapshot_provider = snapshot_provider
        self._persist = persist
        self._pending: set[str] = set()
        self._in_flight: set[str] = set()
        self._generations: dict[str, int] = {}
        self._last_edit_at: dict[str, float] = {}
        self._last_saved_at: dict[str, float] = {}
        self._workers: dict[tuple[str, int], _VersionAutosaveWorker] = {}
        self._quiet = self._timer(self._flush_due)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)

    def schedule(self, tab_id: str) -> None:
        """Aggregate one Assembly edit without performing persistence inline."""

        self._pending.add(tab_id)
        self._generations[tab_id] = self._generations.get(tab_id, 0) + 1
        self._last_edit_at[tab_id] = monotonic()
        self._arm_next_due()

    def flush_now(self) -> None:
        """Explicitly force pending snapshots for an application-controlled flush."""

        self._quiet.stop()
        self._start(tuple(self._pending))
        self._arm_next_due()

    def _flush_due(self) -> None:
        """Persist tabs that are quiet and outside their per-file 120 s window."""

        now = monotonic()
        due = tuple(
            tab_id
            for tab_id in self._pending
            if tab_id not in self._in_flight and self._due_at(tab_id) <= now
        )
        self._start(due)
        self._arm_next_due()

    def _start(self, tab_ids: tuple[str, ...]) -> None:
        for tab_id in tab_ids:
            if tab_id in self._in_flight:
                continue
            self._pending.discard(tab_id)
            snapshot = self._snapshot_provider(tab_id)
            if snapshot is None:
                continue
            self._in_flight.add(tab_id)
            worker = _VersionAutosaveWorker(
                tab_id,
                self._generations[tab_id],
                snapshot,
                self._persist,
            )
            key = (tab_id, self._generations[tab_id])
            self._workers[key] = worker
            worker.signals.saved.connect(self._handle_saved)
            worker.signals.failed.connect(
                lambda message, owner=tab_id, worker_key=key: self._handle_failed(
                    owner,
                    worker_key,
                    message,
                )
            )
            self._pool.start(worker)

    def _handle_saved(self, result: VersionAutosaveResult) -> None:
        self._workers.pop((result.tab_id, result.generation), None)
        self._in_flight.discard(result.tab_id)
        self._last_saved_at[result.tab_id] = monotonic()
        self.saved.emit(result)
        self._arm_next_due()

    def _handle_failed(
        self,
        tab_id: str,
        worker_key: tuple[str, int],
        message: str,
    ) -> None:
        self._workers.pop(worker_key, None)
        self._in_flight.discard(tab_id)
        self.failed.emit(message)
        self._arm_next_due()

    def _due_at(self, tab_id: str) -> float:
        debounce = BINARY_WORKBENCH_TIMING.VERSION_AUTOSAVE_DEBOUNCE_MS / 1000
        interval = BINARY_WORKBENCH_TIMING.VERSION_AUTOSAVE_INTERVAL_MS / 1000
        quiet_at = self._last_edit_at.get(tab_id, monotonic()) + debounce
        rate_limit_at = self._last_saved_at.get(tab_id, float("-inf")) + interval
        return max(quiet_at, rate_limit_at)

    def _arm_next_due(self) -> None:
        waiting = [
            tab_id
            for tab_id in self._pending
            if tab_id not in self._in_flight
        ]
        if not waiting:
            self._quiet.stop()
            return
        delay = max(1, int((min(self._due_at(tab) for tab in waiting) - monotonic()) * 1000))
        self._quiet.start(delay)

    def is_current(self, tab_id: str, generation: int) -> bool:
        """Return whether no newer Assembly edit superseded a saved snapshot."""

        return self._generations.get(tab_id, 0) == generation

    def shutdown(self) -> None:
        """Cancel queued autosaves while allowing a short cooperative exit."""

        self._quiet.stop()
        self._pool.clear()
        self._pool.waitForDone(1000)
        self._workers.clear()

    def _timer(self, callback) -> QTimer:
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(callback)
        return timer
