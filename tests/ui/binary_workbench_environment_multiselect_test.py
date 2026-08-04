import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QAbstractItemView

from src.modules.binary_workbench_dtos import BinaryWorkbenchOffsetRegionDTO
from src.presentation.ui.components.binary_workbench.environment import (
    BinaryWorkbenchOffsetRegionsDialog,
    BinaryWorkbenchSymbolsDialog,
)


def _app() -> QApplication:
    """Return the shared offscreen Qt application."""

    return QApplication.instance() or QApplication([])


def _click_row(dialog, row: int, modifier=Qt.KeyboardModifier.NoModifier) -> None:
    """Click the center of a visible table row with an optional modifier."""

    center = dialog.table.visualRect(dialog.table.model().index(row, 0)).center()
    QTest.mouseClick(dialog.table.viewport(), Qt.MouseButton.LeftButton, modifier, center)
    if modifier == Qt.KeyboardModifier.ControlModifier:
        QTest.keyRelease(dialog.table.viewport(), Qt.Key.Key_Control)
    elif modifier == Qt.KeyboardModifier.ShiftModifier:
        QTest.keyRelease(dialog.table.viewport(), Qt.Key.Key_Shift)


def test_symbols_ctrl_selection_removes_all_selected_rows():
    """Accumulate Symbols rows with Ctrl and remove them in one action."""

    app = _app()
    dialog = BinaryWorkbenchSymbolsDialog({"alpha": "1", "beta": "2", "gamma": "3"}, {}, {})
    dialog.show()
    app.processEvents()
    _click_row(dialog, 0)
    _click_row(dialog, 2, Qt.KeyboardModifier.ControlModifier)

    assert dialog.table.selectionMode() == QAbstractItemView.SelectionMode.ExtendedSelection
    assert {index.row() for index in dialog.table.selectionModel().selectedRows()} == {0, 2}
    dialog.remove_button.click()
    assert dialog.values()[0] == {"beta": "2"}


def test_offset_regions_shift_selection_removes_the_complete_range():
    """Select a contiguous Offset Regions range with Shift before removal."""

    app = _app()
    regions = [BinaryWorkbenchOffsetRegionDTO(f"r{index}", index, "") for index in range(5)]
    dialog = BinaryWorkbenchOffsetRegionsDialog(regions, "")
    dialog.show()
    app.processEvents()
    _click_row(dialog, 1)
    _click_row(dialog, 3, Qt.KeyboardModifier.ShiftModifier)

    assert {index.row() for index in dialog.table.selectionModel().selectedRows()} == {1, 2, 3}
    dialog.remove_button.click()
    assert [region.name for region in dialog.mappings()] == ["r0", "r4"]
