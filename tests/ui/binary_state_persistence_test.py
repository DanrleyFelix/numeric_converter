import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication

from src.modules.binary_workbench_dtos import BinaryWorkbenchStateDTO
from src.presentation.ui.main_window.binary_state import (
    BinaryStatePersistenceScheduler,
)


def _app() -> QApplication:
    """Return the shared offscreen Qt application."""

    return QApplication.instance() or QApplication([])


def test_binary_state_persistence_coalesces_before_serialization():
    """Persist only the latest state emitted by one Binary event burst."""

    app = _app()
    saved: list[str | None] = []
    owner = QObject()
    scheduler = BinaryStatePersistenceScheduler(
        lambda state: saved.append(state.active_tab_id),
        owner,
        debounce_ms=10_000,
    )

    scheduler.schedule(BinaryWorkbenchStateDTO(active_tab_id="old"))
    scheduler.schedule(BinaryWorkbenchStateDTO(active_tab_id="current"))

    assert saved == []
    scheduler.flush_due()
    assert scheduler._pool.waitForDone(2_000)
    app.processEvents()
    assert saved == ["current"]
    scheduler.shutdown()


def test_binary_state_persistence_flushes_newest_pending_state_on_close():
    """Close persists the latest pending snapshot without replaying old ones."""

    _app()
    saved: list[str | None] = []
    owner = QObject()
    scheduler = BinaryStatePersistenceScheduler(
        lambda state: saved.append(state.active_tab_id),
        owner,
        debounce_ms=10_000,
    )
    scheduler.schedule(BinaryWorkbenchStateDTO(active_tab_id="first"))
    scheduler.schedule(BinaryWorkbenchStateDTO(active_tab_id="last"))

    result = scheduler.flush_on_close()

    assert result.error is None
    assert saved == ["last"]
    scheduler.shutdown()
