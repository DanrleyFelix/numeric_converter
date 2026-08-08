from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import QObject, QTimer, Signal

from src.modules.binary_workbench_dtos import BinaryWorkbenchTabContextDTO
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_TIMING,
)


@dataclass(frozen=True)
class VersionAutosaveResult:
    """Describe one completed Assembly-source autosave."""

    tab_id: str
    generation: int
    module_paths: dict[str, str]


class VersionAutosaveScheduler(QObject):
    """Save only Assembly source after five seconds without typing.

    Autosave is deliberately a GUI-thread timer, not a worker.  The callback
    snapshots the authoritative Assembly document and writes only the active
    version module; it never assembles code or refreshes derived columns.
    """

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
        self._generations: dict[str, int] = {}
        self._quiet = QTimer(self)
        self._quiet.setSingleShot(True)
        self._quiet.setInterval(
            BINARY_WORKBENCH_TIMING.VERSION_AUTOSAVE_DEBOUNCE_MS
        )
        self._quiet.timeout.connect(self.flush_now)

    def schedule(self, tab_id: str) -> None:
        """Restart the one idle deadline without doing persistence work."""

        self._pending.add(tab_id)
        self._generations[tab_id] = self._generations.get(tab_id, 0) + 1
        self._quiet.start()

    def flush_now(self) -> None:
        """Persist each pending source snapshot once, without a worker."""

        self._quiet.stop()
        pending = tuple(self._pending)
        self._pending.clear()
        for tab_id in pending:
            snapshot = self._snapshot_provider(tab_id)
            if snapshot is None:
                continue
            generation = self._generations.get(tab_id, 0)
            try:
                paths = self._persist(snapshot)
            except Exception as error:
                self.failed.emit(str(error))
                continue
            self.saved.emit(VersionAutosaveResult(tab_id, generation, paths))

    def is_current(self, tab_id: str, generation: int) -> bool:
        """Return whether no newer Assembly edit followed the saved source."""

        return self._generations.get(tab_id, 0) == generation

    def shutdown(self) -> None:
        """Discard an idle autosave when the owning Binary window closes."""

        self._quiet.stop()
        self._pending.clear()
