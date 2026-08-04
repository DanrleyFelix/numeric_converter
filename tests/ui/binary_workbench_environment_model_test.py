import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication

from src.modules.binary_workbench_dtos import BinaryWorkbenchInternalFileDTO
from src.presentation.ui.components.binary_workbench.environment_table.model import EnvironmentTableModel
from src.presentation.ui.components.binary_workbench.file_dialogs import BinaryWorkbenchLbaFilesystemDialog


def _app() -> QApplication:
    """Return the shared offscreen Qt application."""

    return QApplication.instance() or QApplication([])


def test_environment_model_edits_records_incrementally_without_reset():
    """Use row and cell signals instead of rebuilding the complete model."""

    model = EnvironmentTableModel(("Name", "Value"), {0, 1})
    resets = QSignalSpy(model.modelReset)
    inserted = QSignalSpy(model.rowsInserted)
    removed = QSignalSpy(model.rowsRemoved)
    changed = QSignalSpy(model.dataChanged)
    record_id = model.append(["alpha", "1"])
    assert model.setData(model.index(0, 1), "2") is True
    assert model.remove(record_id) is True

    assert resets.count() == 0
    assert inserted.count() == 1
    assert changed.count() == 1
    assert removed.count() == 1


def test_sorted_lba_selection_maps_to_the_stable_source_record():
    """Navigate the intended record after the proxy changes row order."""

    _app()
    dialog = BinaryWorkbenchLbaFilesystemDialog(
        [BinaryWorkbenchInternalFileDTO("alpha", 1), BinaryWorkbenchInternalFileDTO("zulu", 9)]
    )
    offsets: list[int] = []
    dialog.goToRequested.connect(offsets.append)
    dialog.table.sortByColumn(0, Qt.SortOrder.DescendingOrder)
    dialog.table.selectRow(0)
    dialog.go_to_button.click()

    assert offsets == [9 * dialog.selected_lba_sector_size()]
