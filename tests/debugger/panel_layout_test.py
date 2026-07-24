"""Focused geometry tests for the lower debugger panel."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtWidgets import QApplication, QStyleOptionViewItem

from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT
from src.presentation.ui.components.debugger.panels.tabs.widget import DebuggerLowerTabs
from helpers import BASE, configured_debugger

_APP = None


def _app() -> QApplication:
    """Return the shared offscreen application."""

    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


def _column_gap(table) -> int:
    """Return the viewport width left between columns and the scrollbar."""

    return table.viewport().width() - sum(
        table.columnWidth(column) for column in range(table.columnCount())
    )


def _show_tabs(width: int = 900) -> DebuggerLowerTabs:
    """Create visible lower tabs at a stable test geometry."""

    app = _app()
    debugger = configured_debugger("nop")
    tabs = DebuggerLowerTabs(debugger, debugger._image)
    tabs.resize(width, 420)
    tabs.show()
    app.processEvents()
    return tabs


def _assert_table_geometry(table) -> None:
    """Confirm the reserved gap and standard cursors for one table."""

    assert _column_gap(table) == DEBUGGER_LAYOUT.TABLE_SCROLLBAR_GAP
    assert table.cursor().shape() == Qt.ArrowCursor
    assert table.viewport().cursor().shape() == Qt.ArrowCursor
    assert table.horizontalHeader().cursor().shape() == Qt.ArrowCursor
    assert table.verticalScrollBar().cursor().shape() == Qt.ArrowCursor


def test_lower_tables_follow_three_window_widths_without_losing_gap():
    """Keep every lower table attached to the same scrollbar boundary."""

    app = _app()
    tabs = _show_tabs(720)
    for width in (720, 900, 1400):
        tabs.resize(width, 420)
        app.processEvents()
        tabs.setCurrentWidget(tabs.stack)
        tabs.stack._resize_columns()
        _assert_table_geometry(tabs.stack)
        tabs.setCurrentWidget(tabs.memory)
        app.processEvents()
        _assert_table_geometry(tabs.memory.table)
        tabs.setCurrentWidget(tabs.breakpoints)
        app.processEvents()
        _assert_table_geometry(tabs.breakpoints.table)


def test_manual_header_resize_is_compensated_and_bounded():
    """Compensate manual divider movement without changing total table width."""

    tabs = _show_tabs(1400)
    tables = (
        (
            tabs.stack,
            2,
            DEBUGGER_LAYOUT.STACK_COLUMN_MINIMUMS,
            DEBUGGER_LAYOUT.STACK_COLUMN_MAXIMUMS,
        ),
        (
            tabs.memory.table,
            1,
            DEBUGGER_LAYOUT.MEMORY_COLUMN_MINIMUMS,
            DEBUGGER_LAYOUT.MEMORY_COLUMN_MAXIMUMS,
        ),
        (
            tabs.breakpoints.table,
            1,
            DEBUGGER_LAYOUT.BREAKPOINT_COLUMN_MINIMUMS,
            DEBUGGER_LAYOUT.BREAKPOINT_COLUMN_MAXIMUMS,
        ),
    )
    for table, column, minimums, maximums in tables:
        if table is tabs.memory.table:
            tabs.setCurrentWidget(tabs.memory)
            QApplication.processEvents()
        elif table is tabs.breakpoints.table:
            tabs.setCurrentWidget(tabs.breakpoints)
            QApplication.processEvents()
        before = tuple(
            table.columnWidth(index) for index in range(table.columnCount())
        )
        total = sum(before)
        table.horizontalHeader().resizeSection(column, table.columnWidth(column) + 40)
        after = tuple(table.columnWidth(index) for index in range(table.columnCount()))
        assert any(after[index] < before[index] for index in range(len(after)) if index != column)
        assert sum(
            table.columnWidth(index) for index in range(table.columnCount())
        ) == total
        table.horizontalHeader().resizeSection(column, 1)
        assert table.columnWidth(column) == minimums[column]
        table.horizontalHeader().resizeSection(column, maximums[column] + 500)
        assert minimums[column] <= table.columnWidth(column) <= maximums[column]
        _assert_table_geometry(table)


def test_cell_editors_fill_cells_and_log_icon_keeps_exact_margin():
    """Fill editing rectangles and reserve the Search Log icon area."""

    tabs = _show_tabs()
    memory_delegate = tabs.memory.table.itemDelegate()
    option = QStyleOptionViewItem()
    option.rect = QRect(3, 4, 220, DEBUGGER_LAYOUT.LOWER_TABLE_ROW_HEIGHT)
    memory_editor = memory_delegate.createEditor(tabs.memory.table, option, None)
    memory_delegate.updateEditorGeometry(memory_editor, option, None)
    assert memory_editor.geometry() == option.rect
    assert memory_editor.objectName() == "debugger-cell-editor"

    tabs.breakpoints._debugger.add_breakpoint(BASE)
    tabs.breakpoints.refresh()
    name_delegate = tabs.breakpoints.table.itemDelegateForColumn(1)
    name_editor = name_delegate.createEditor(tabs.breakpoints.table, option, None)
    name_delegate.updateEditorGeometry(name_editor, option, None)
    assert name_editor.geometry() == option.rect

    tabs.setCurrentWidget(tabs.memory)
    QApplication.processEvents()
    margins = tabs.filter.follow.layout().contentsMargins()
    read_position = tabs.filter.follow_read.mapTo(tabs.filter, QPoint())
    assert margins.top() == DEBUGGER_LAYOUT.MEMORY_FOLLOW_VERTICAL_MARGIN
    assert margins.right() == DEBUGGER_LAYOUT.MEMORY_FOLLOW_RIGHT_MARGIN
    assert (
        tabs.filter.width() - read_position.x() - tabs.filter.follow_read.width()
        == DEBUGGER_LAYOUT.MEMORY_FOLLOW_RIGHT_MARGIN
    )

    tabs.setCurrentWidget(tabs.log)
    QApplication.processEvents()
    search = tabs.filter.search
    icon = search._search_icon
    assert search.width() - icon.geometry().right() - 1 == DEBUGGER_LAYOUT.LOG_FILTER_ICON_MARGIN
    assert search.textMargins().right() > icon.width() + DEBUGGER_LAYOUT.LOG_FILTER_ICON_MARGIN
