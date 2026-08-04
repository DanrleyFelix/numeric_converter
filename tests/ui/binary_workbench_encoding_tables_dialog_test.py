import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QListWidget, QPushButton, QScrollArea, QWidget

from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ANSI_TABLE_NAME
from src.modules.binary_workbench_dtos import BinaryWorkbenchEncodingTableDTO
from src.presentation.ui.components.binary_workbench.environment.encoding_tables.dialog import (
    BinaryWorkbenchEncodingTablesDialog,
)
from src.presentation.ui.components.binary_workbench.environment.encoding_tables.list_view import (
    CONFLICT_ROLE,
)
from src.presentation.ui.helpers.load_qss import STYLESHEET, THEME_TOKENS


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _tables(count: int) -> list[BinaryWorkbenchEncodingTableDTO]:
    return [
        BinaryWorkbenchEncodingTableDTO(f"table_{index}", {index % 256: str(index)})
        for index in range(count)
    ]


def test_encoding_tables_use_one_virtualized_list_without_row_widgets():
    _app()
    small = BinaryWorkbenchEncodingTablesDialog(_tables(1), [], "")
    large = BinaryWorkbenchEncodingTablesDialog(_tables(1000), [], "")

    assert isinstance(large.tables_list, QListWidget)
    assert large.tables_list.count() == 1001
    assert large.findChildren(QScrollArea) == []
    assert len(small.findChildren(QWidget)) == len(large.findChildren(QWidget))
    assert len(large.findChildren(QPushButton)) == 1
    assert all(
        large.tables_list.itemWidget(large.tables_list.item(row)) is None
        for row in range(1001)
    )
    assert large.tables_list.spacing() == 0
    assert large.tables_list.uniformItemSizes() is True
    assert large.tables_list.item(0).sizeHint().height() == large.tables_list.fontMetrics().height() * 2


def test_simple_click_toggles_multiple_encoding_tables_independently():
    app = _app()
    dialog = BinaryWorkbenchEncodingTablesDialog(
        [
            BinaryWorkbenchEncodingTableDTO("first", {0: "A"}),
            BinaryWorkbenchEncodingTableDTO("second", {1: "B"}),
        ],
        [],
        "",
    )
    dialog.show()
    app.processEvents()

    for row in (1, 2):
        QTest.mouseClick(
            dialog.tables_list.viewport(),
            Qt.MouseButton.LeftButton,
            pos=dialog.tables_list.visualItemRect(dialog.tables_list.item(row)).center(),
        )
        app.processEvents()

    assert dialog.enabled_names() == ["first", "second"]
    assert [item.text() for item in dialog.tables_list.selectedItems()] == ["first", "second"]

    QTest.mouseClick(
        dialog.tables_list.viewport(),
        Qt.MouseButton.LeftButton,
        pos=dialog.tables_list.visualItemRect(dialog.tables_list.item(1)).center(),
    )
    assert dialog.enabled_names() == ["second"]
    dialog.close()


def test_conflicting_table_restores_selection_and_marks_only_that_row():
    _app()
    dialog = BinaryWorkbenchEncodingTablesDialog(
        [BinaryWorkbenchEncodingTableDTO("conflict", {0x41: "custom-A"})],
        [BINARY_WORKBENCH_ANSI_TABLE_NAME],
        "",
    )

    dialog._toggle("conflict")

    item = dialog._items["conflict"]
    assert "conflict" not in dialog.enabled_names()
    assert item.isSelected() is False
    assert item.data(CONFLICT_ROLE) is True


def test_selected_encoding_color_differs_from_hover_and_panel_has_no_radius():
    _app()
    assert THEME_TOKENS["bg-toolbar-button-hover"] != THEME_TOKENS["bg-search-result-hover"]
    assert "QListWidget#binary-workbench-encoding-tables::item:hover" in STYLESHEET
    assert "QListWidget#binary-workbench-encoding-tables::item:selected" in STYLESHEET
    encoding_section = STYLESHEET.split("QListWidget#binary-workbench-encoding-tables", 1)[1]
    assert "border-radius: 0px" in encoding_section
    assert "padding-left: 12px" in encoding_section
