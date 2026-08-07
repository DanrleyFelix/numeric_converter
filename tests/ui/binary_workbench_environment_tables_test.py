import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton, QScrollArea, QTableView, QWidget

from src.modules.binary_workbench_dtos import BinaryWorkbenchInternalFileDTO, BinaryWorkbenchOffsetRegionDTO
from src.presentation.ui.components.binary_workbench.button_icon_painting import ICON_TEXT_SPACING_PROPERTY
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT, BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.environment import (
    BinaryWorkbenchCommandsDialog,
    BinaryWorkbenchLabelsDialog,
    BinaryWorkbenchOffsetRegionsDialog,
)
from src.presentation.ui.components.binary_workbench.file_dialogs import BinaryWorkbenchLbaFilesystemDialog
from src.presentation.ui.helpers.load_qss import STYLESHEET


def _app() -> QApplication:
    """Return the shared offscreen Qt application."""

    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize(
    ("small_factory", "large_factory", "model_name"),
    (
        (
            lambda: BinaryWorkbenchLbaFilesystemDialog([BinaryWorkbenchInternalFileDTO("one", 1)]),
            lambda: BinaryWorkbenchLbaFilesystemDialog([BinaryWorkbenchInternalFileDTO(f"file_{i}", i) for i in range(1000)]),
            "lba_model",
        ),
        (
            lambda: BinaryWorkbenchCommandsDialog({"one": ["nop"]}, ""),
            lambda: BinaryWorkbenchCommandsDialog({f"command_{i}": ["nop"] for i in range(1000)}, ""),
            "commands_model",
        ),
        (
            lambda: BinaryWorkbenchOffsetRegionsDialog([BinaryWorkbenchOffsetRegionDTO("one", 1, "")], ""),
            lambda: BinaryWorkbenchOffsetRegionsDialog([BinaryWorkbenchOffsetRegionDTO(f"region_{i}", i, "") for i in range(1000)], ""),
            "regions_model",
        ),
        (
            lambda: BinaryWorkbenchLabelsDialog({"one": "0x1"}),
            lambda: BinaryWorkbenchLabelsDialog({f"label_{i}": hex(i) for i in range(1000)}),
            "labels_model",
        ),
    ),
)
def test_environment_tables_virtualize_one_thousand_records(small_factory, large_factory, model_name):
    """Keep permanent widget counts independent of the record count."""

    _app()
    small = small_factory()
    large = large_factory()
    table = large.findChild(QTableView, "binary-workbench-environment-table")
    margins = large.shell.layout().contentsMargins()

    assert getattr(large, model_name).rowCount() == 1000
    assert table is not None
    assert table.horizontalHeader().objectName() == "binary-workbench-environment-header"
    assert table.indexWidget(table.model().index(0, 0)) is None
    assert large.findChildren(QScrollArea) == []
    assert large.findChildren(QWidget, "workspace-row") == []
    assert len(small.findChildren(QWidget)) == len(large.findChildren(QWidget))
    assert len(small.findChildren(QLineEdit)) == len(large.findChildren(QLineEdit))
    assert len(small.findChildren(QPushButton)) == len(large.findChildren(QPushButton))
    assert (margins.left(), margins.top(), margins.right(), margins.bottom()) == (20, 20, 20, 20)
    small.close()
    large.close()


def test_environment_table_header_keeps_the_dark_project_background():
    """Catch the white native header regression after assigning its object name."""

    _app()
    dialog = BinaryWorkbenchLabelsDialog({"entry": "0x0"})
    dialog.setStyleSheet(STYLESHEET)
    dialog.show()
    _app().processEvents()
    header = dialog.table.horizontalHeader()
    image = header.grab().toImage()

    assert image.pixelColor(5, 5).name().lower() == "#1d1d2c"
    dialog.close()


def test_lba_table_adds_filters_removes_and_navigates_selected_record():
    """Drive all LBA record actions through the proxy/source selection."""

    _app()
    dialog = BinaryWorkbenchLbaFilesystemDialog([BinaryWorkbenchInternalFileDTO("SLUS", 24)])
    navigated: list[int] = []
    dialog.goToRequested.connect(navigated.append)
    dialog.table.selectRow(0)
    dialog.go_to_button.click()
    dialog.name.setText("SYSTEM.CNF")
    dialog.lba.setText("40")
    next(button for button in dialog.findChildren(QPushButton) if button.text() == BINARY_WORKBENCH_TEXT.SYMBOL_ADD).click()
    dialog.filter_input.setText("SYSTEM")

    assert navigated == [24 * dialog.selected_lba_sector_size()]
    assert dialog.lba_proxy.rowCount() == 1
    assert dialog.mappings()[-1] == BinaryWorkbenchInternalFileDTO("SYSTEM.CNF", 40)

    dialog.table.selectRow(0)
    dialog.remove_button.click()
    assert all(item.name != "SYSTEM.CNF" for item in dialog.mappings())


def test_commands_table_filters_and_emits_actions_for_stable_selection(monkeypatch):
    """Resolve Show and Remove after filtering without per-row buttons."""

    _app()
    from src.presentation.ui.components.binary_workbench.environment.commands import dialog as module

    monkeypatch.setattr(module, "edit_command_instructions", lambda name, lines, parent: lines + ["jr $ra"])
    dialog = BinaryWorkbenchCommandsDialog({"alpha": ["nop"], "beta": ["addiu $v0, $zero, 1"]}, "")
    removed: list[str] = []
    changed: list[tuple[str, list[str]]] = []
    dialog.commandRemoveRequested.connect(removed.append)
    dialog.commandInstructionsChangeRequested.connect(lambda name, lines: changed.append((name, lines)))
    dialog.filter_input.setText("beta")
    dialog.table.selectRow(0)
    dialog.show_button.click()
    dialog.remove_button.click()

    assert dialog.commands_proxy.rowCount() == 1
    assert dialog.show_button.parentWidget() is dialog.filter_input.parentWidget()
    assert dialog.remove_button.parentWidget() is dialog.filter_input.parentWidget()
    assert changed == [("beta", ["addiu $v0, $zero, 1", "jr $ra"])]
    assert removed == ["beta"]


def test_offset_regions_and_labels_use_fixed_selection_actions():
    """Navigate regions by action and labels by table double click."""

    _app()
    regions = BinaryWorkbenchOffsetRegionsDialog([BinaryWorkbenchOffsetRegionDTO("code", 0x40, "")], "")
    labels = BinaryWorkbenchLabelsDialog({"loop": "0x80"})
    region_offsets: list[int] = []
    label_offsets: list[int] = []
    regions.goToRequested.connect(region_offsets.append)
    labels.goToRequested.connect(label_offsets.append)
    regions.show()
    _app().processEvents()
    regions.table.selectRow(0)
    _app().processEvents()
    regions.go_to_button.click()
    labels.show()
    _app().processEvents()
    label_center = labels.table.visualRect(labels.labels_proxy.index(0, 0)).center()
    QTest.mouseClick(labels.table.viewport(), Qt.MouseButton.LeftButton, pos=label_center)
    QTest.mouseDClick(labels.table.viewport(), Qt.MouseButton.LeftButton, pos=label_center)

    assert region_offsets == [0x40]
    assert label_offsets == [0x80]
    assert regions.mappings()[0].name == "code"


def test_environment_actions_reuse_symbols_icons_and_spacing():
    """Keep all fixed actions identifiable and centered like Symbols."""
    _app()
    dialogs = (
        BinaryWorkbenchLbaFilesystemDialog([]),
        BinaryWorkbenchCommandsDialog({}, ""),
        BinaryWorkbenchOffsetRegionsDialog([], ""),
        BinaryWorkbenchLabelsDialog({}),
    )
    for dialog in dialogs:
        actions = [button for button in dialog.findChildren(QPushButton) if button.text()]
        assert BINARY_WORKBENCH_TEXT.OK not in {button.text() for button in actions}
        assert all(not button.icon().isNull() for button in actions)
        assert all(button.property(ICON_TEXT_SPACING_PROPERTY) == BINARY_WORKBENCH_LAYOUT.SYMBOL_ACTION_ICON_TEXT_SPACING for button in actions)


def test_offset_regions_entry_anchors_name_and_details_to_table_edges():
    _app()
    dialog = BinaryWorkbenchOffsetRegionsDialog([], "")
    dialog.resize(dialog.maximumWidth(), dialog.height())
    dialog.show()
    _app().processEvents()

    assert dialog.name.mapTo(dialog, QPoint()).x() == dialog.table.mapTo(dialog, QPoint()).x()
    assert (
        dialog.details_button.mapTo(dialog, QPoint()).x()
        + dialog.details_button.width()
        == dialog.table.mapTo(dialog, QPoint()).x() + dialog.table.width()
    )
    add_button = next(
        button
        for button in dialog.findChildren(QPushButton)
        if button.text() == BINARY_WORKBENCH_TEXT.SYMBOL_ADD
    )
    assert dialog.remove_button.parentWidget() is dialog.details_button.parentWidget()
    add_right = add_button.mapTo(dialog, QPoint()).x() + add_button.width()
    remove_left = dialog.remove_button.mapTo(dialog, QPoint()).x()
    remove_right = remove_left + dialog.remove_button.width()
    details_left = dialog.details_button.mapTo(dialog, QPoint()).x()
    assert abs((remove_left - add_right) - (details_left - remove_right)) <= 1


def test_offset_regions_filter_fills_the_footer_to_the_table_right_edge():
    _app()
    dialog = BinaryWorkbenchOffsetRegionsDialog([], "")
    dialog.resize(dialog.maximumWidth(), dialog.height())
    dialog.show()
    _app().processEvents()

    filter_right = (
        dialog.filter_input.mapTo(dialog, QPoint()).x()
        + dialog.filter_input.width()
    )
    table_right = dialog.table.mapTo(dialog, QPoint()).x() + dialog.table.width()

    assert filter_right == table_right
    assert dialog.filter_input.width() > BINARY_WORKBENCH_LAYOUT.SHARED_FILTER_WIDTH


def test_commands_dialog_width_keeps_filter_inside_the_table_edge():
    _app()
    dialog = BinaryWorkbenchCommandsDialog({}, "")
    dialog.show()
    _app().processEvents()

    assert dialog.width() == BINARY_WORKBENCH_LAYOUT.COMMANDS_DIALOG_WIDTH
    assert dialog.filter_input.width() > BINARY_WORKBENCH_LAYOUT.SHARED_FILTER_WIDTH
    assert (
        dialog.filter_input.mapTo(dialog, QPoint()).x()
        + dialog.filter_input.width()
        == dialog.table.mapTo(dialog, QPoint()).x() + dialog.table.width()
    )
    assert dialog.filter_input.maximumWidth() == BINARY_WORKBENCH_LAYOUT.COMMANDS_DIALOG_WIDTH
    assert abs(
        dialog.table.columnWidth(0) - dialog.table.viewport().width() // 4
    ) <= 1
    assert dialog.table.columnWidth(1) > dialog.table.columnWidth(0) * 2
