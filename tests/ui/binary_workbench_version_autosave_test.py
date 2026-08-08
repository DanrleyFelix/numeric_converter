import os

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


def test_version_autosave_waits_five_seconds_of_idle_before_snapshot():
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
    assert 4_000 <= scheduler._quiet.remainingTime() <= 5_000
    saved: list[object] = []
    scheduler.saved.connect(saved.append)
    scheduler.flush_now()
    assert _wait_for(saved)
    assert snapshots == ["tab"]
    assert persisted == ["tab"]

    scheduler.schedule("tab")
    QTest.qWait(20)
    assert snapshots == ["tab"]
    assert scheduler._quiet.isActive()
    scheduler.shutdown()


def test_version_autosave_has_no_worker_or_thread_pool():
    _app()
    parent = QWidget()
    persisted: list[str] = []

    def persist(context):
        persisted.append(context.tab_id)
        return {"versions": "versions.json"}

    scheduler = VersionAutosaveScheduler(lambda tab: _context(tab), persist, parent)
    saved: list[object] = []
    scheduler.saved.connect(saved.append)
    scheduler.schedule("tab")
    scheduler.flush_now()

    assert _wait_for(saved)
    assert persisted == ["tab"]
    assert not hasattr(scheduler, "_pool")
    scheduler.shutdown()
