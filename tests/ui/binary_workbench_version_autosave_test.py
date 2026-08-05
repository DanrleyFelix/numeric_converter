import os
from threading import get_ident
from time import monotonic

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from src.modules.binary_workbench_dtos import BinaryWorkbenchTabContextDTO
from src.presentation.ui.components.binary_workbench.tabs.autosave import (
    VersionAutosaveScheduler,
)

_APP = None


def _app() -> QApplication:
    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


def _context(tab_id: str = "tab") -> BinaryWorkbenchTabContextDTO:
    return BinaryWorkbenchTabContextDTO(tab_id, "assembly", "source.asm")


def _wait_for(values: list, timeout_ms: int = 1_000) -> bool:
    for _ in range(max(1, timeout_ms // 20)):
        if values:
            return True
        QTest.qWait(20)
    return bool(values)


def test_version_autosave_uses_quiet_debounce_then_per_file_rate_limit():
    _app()
    parent = QWidget()
    snapshots: list[str] = []
    persisted: list[str] = []

    def snapshot(tab_id: str):
        snapshots.append(tab_id)
        return _context(tab_id)

    def persist(context):
        persisted.append(context.tab_id)
        return {}

    scheduler = VersionAutosaveScheduler(snapshot, persist, parent)
    scheduler.schedule("tab")

    assert snapshots == []
    assert scheduler._quiet.remainingTime() > 9_000
    scheduler._flush_due()
    assert snapshots == []

    scheduler._last_edit_at["tab"] = monotonic() - 11
    saved: list[object] = []
    scheduler.saved.connect(saved.append)
    scheduler._flush_due()
    assert _wait_for(saved)
    assert snapshots == ["tab"]
    assert persisted == ["tab"]

    scheduler.schedule("tab")
    scheduler._last_edit_at["tab"] = monotonic() - 11
    scheduler._flush_due()
    QTest.qWait(20)
    assert snapshots == ["tab"]
    assert scheduler._due_at("tab") > monotonic() + 50
    scheduler.shutdown()


def test_version_autosave_persistence_runs_outside_main_thread():
    _app()
    parent = QWidget()
    main_thread = get_ident()
    worker_threads: list[int] = []

    def persist(_context):
        worker_threads.append(get_ident())
        return {"versions": "versions.json"}

    scheduler = VersionAutosaveScheduler(lambda tab: _context(tab), persist, parent)
    saved: list[object] = []
    scheduler.saved.connect(saved.append)
    scheduler.schedule("tab")
    scheduler.flush_now()

    assert _wait_for(saved)
    assert worker_threads and worker_threads[0] != main_thread
    scheduler.shutdown()
