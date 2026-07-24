"""Window-level geometry checks for debugger panel scrollbars."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

from src.core.debugger.directives.parser import parse_debugger_directives
from src.core.debugger.session.factory import DebuggerSessionBundle
from src.presentation.repository.debugger_window.repository import (
    DebuggerWindowStateRepository,
)
from src.presentation.ui.components.debugger.actions import (
    DebuggerActions,
)
from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT
from src.presentation.ui.components.debugger.window import DebuggerWindow
from helpers import BASE, configured_debugger

_APP = None


def _app() -> QApplication:
    """Return the shared offscreen application."""

    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


def _window(tmp_path) -> DebuggerWindow:
    """Create a populated debugger window for scrollbar measurements."""

    app = _app()
    debugger = configured_debugger("nop")
    for index in range(24):
        debugger.add_breakpoint(BASE + index * 4)
        debugger.record_event("Info", f"layout event {index}")
    bundle = DebuggerSessionBundle(
        debugger,
        parse_debugger_directives(
            [
                f"* virtual_memory_range "
                f"0x{debugger._image.start:X} 0x{debugger._image.end:X}"
            ]
        ),
        (),
        debugger._image,
    )
    return DebuggerWindow(
        bundle,
        DebuggerActions(app),
        DebuggerWindowStateRepository(tmp_path / "debugger-layout.json"),
        "layout",
    )


def _assert_table_scrollbar(table) -> None:
    """Confirm both ten-pixel gaps around one visible scrollbar."""

    scrollbar = table.verticalScrollBar()
    scrollbar_left = scrollbar.mapTo(table, QPoint()).x()
    content_end = table.viewport().x() + sum(
        table.columnWidth(column) for column in range(table.columnCount())
    )
    assert scrollbar.isVisible()
    assert scrollbar_left - content_end == DEBUGGER_LAYOUT.TABLE_SCROLLBAR_GAP
    assert (
        table.width() - scrollbar_left - scrollbar.width()
        == DEBUGGER_LAYOUT.TABLE_SCROLLBAR_GAP
    )


def _assert_log_scrollbar(output) -> None:
    """Confirm the log keeps equivalent content and panel spacing."""

    scrollbar = output.verticalScrollBar()
    scrollbar_left = scrollbar.mapTo(output, QPoint()).x()
    assert scrollbar.isVisible()
    assert (
        output.width() - scrollbar_left - scrollbar.width()
        == DEBUGGER_LAYOUT.TABLE_SCROLLBAR_GAP
    )
    assert output.contentsMargins().right() == DEBUGGER_LAYOUT.TABLE_SCROLLBAR_GAP


def test_panel_scrollbars_remain_fixed_at_three_window_sizes(tmp_path):
    """Keep table and panel gaps exact from minimum through ample width."""

    app = _app()
    window = _window(tmp_path)
    window.show()
    for width, height in ((900, 620), (1280, 820), (1800, 1000)):
        window.resize(width, height)
        app.processEvents()
        lower = window.panels.lower
        lower.setCurrentWidget(lower.stack)
        lower.stack._resize_columns()
        _assert_table_scrollbar(lower.stack)
        lower.setCurrentWidget(lower.memory)
        app.processEvents()
        _assert_table_scrollbar(lower.memory.table)
        lower.setCurrentWidget(lower.breakpoints)
        app.processEvents()
        _assert_table_scrollbar(lower.breakpoints.table)
        lower.setCurrentWidget(lower.log)
        app.processEvents()
        _assert_log_scrollbar(lower.log.output)
    window.close()
