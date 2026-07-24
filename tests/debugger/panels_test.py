import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QHelpEvent, QKeyEvent, QTextDocument, QValidator
from PySide6.QtWidgets import QApplication, QToolButton

from src.presentation.ui.components.binary_workbench.editor.highlighters import (
    BytesHighlighter,
    InstructionHighlighter,
)
from src.presentation.ui.components.debugger.actions import (
    DebuggerActionBar,
    DebuggerActions,
)
from src.core.debugger.directives.parser import parse_debugger_directives
from src.core.debugger.models.session import DebuggerEvent
from src.core.debugger.session.factory import DebuggerSessionBundle
from src.presentation.repository.debugger_window.repository import (
    DebuggerWindowStateRepository,
)
from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT
from src.presentation.ui.components.debugger.config.dialog import DebuggerConfigDialog
from src.presentation.ui.components.debugger.panels.instruction.highlighting import (
    SyntaxCellDelegate,
)
from src.presentation.ui.components.debugger.panels.instructions import DebuggerInstructionPanel
from src.presentation.ui.components.debugger.panels.log.view import DebuggerLogHighlighter
from src.presentation.ui.components.debugger.panels.memory.view import DebuggerMemoryView
from src.presentation.ui.components.debugger.panels.registers import DebuggerRegisterPanel
from src.presentation.ui.components.debugger.panels.session.breakpoint.presentation import (
    BreakpointNameDelegate,
)
from src.presentation.ui.components.debugger.panels.tabs.widget import DebuggerLowerTabs
from src.presentation.ui.components.debugger.window import DebuggerWindow
from helpers import BASE, configured_debugger

_APP = None


def _app() -> QApplication:
    """Return the shared application for debugger panel tests."""

    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


def _content_to_scrollbar_gap(table) -> int:
    """Measure the viewport space intentionally left after the last column."""

    return table.viewport().width() - sum(
        table.columnWidth(column) for column in range(table.columnCount())
    )


def test_instruction_panel_uses_exec_status_width_limits_and_bytes_delegate():
    """Keep instruction columns readable and render repeated execution distinctly."""

    _app()
    debugger = configured_debugger("nop", "nop")
    debugger.statistics.executed[BASE] = 3
    panel = DebuggerInstructionPanel()
    panel.refresh(debugger, BASE)
    panel.resize(1000, 400)
    panel.show()
    QApplication.processEvents()

    assert panel.item(0, 5).text() == "EXEC (3)"
    assert panel.item(0, 5).foreground().color().name().upper() == "#1E90FF"
    assert panel.columnWidth(0) >= DEBUGGER_LAYOUT.INSTRUCTION_NUMBER_MIN_WIDTH
    assert panel.columnWidth(3) == DEBUGGER_LAYOUT.RAW_INSTRUCTION_WIDTH
    assert panel.columnWidth(4) >= DEBUGGER_LAYOUT.INSTRUCTION_ORIGIN_MIN_WIDTH
    assert panel.columnWidth(5) == DEBUGGER_LAYOUT.INSTRUCTION_STATUS_WIDTH
    assert _content_to_scrollbar_gap(panel) == DEBUGGER_LAYOUT.TABLE_SCROLLBAR_GAP
    assert not panel.horizontalHeader().stretchLastSection()
    assert panel.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
    delegate = panel.itemDelegateForColumn(2)
    assert isinstance(delegate, SyntaxCellDelegate)
    assert delegate._highlighter_type is BytesHighlighter
    debugger.statistics.executed.clear()
    panel.refresh(debugger)
    assert panel.item(0, 5).text() == "ACTUAL"
    assert panel.item(1, 5).text() == "READY"
    debugger.add_breakpoint(BASE + 4)
    panel.refresh(debugger)
    assert panel.item(1, 5).text() == "BREAKPOINT"
    assert panel.item(1, 5).foreground().color().name().upper() == "#F0C75E"
    debugger.step()
    panel.refresh(debugger)
    assert panel.item(1, 5).text() == "BREAK"
    assert panel.item(1, 5).foreground().color().name().upper() == "#F4A261"
    debugger.toggle_ignored_instruction(BASE + 4)
    panel.refresh(debugger)
    assert panel.item(1, 5).text().startswith("IGNORED")
    assert panel.columnWidth(5) == DEBUGGER_LAYOUT.INSTRUCTION_STATUS_WIDTH
    debugger.statistics.executed.clear()
    debugger.pc = BASE + 8
    panel.refresh(debugger, BASE)
    assert panel.item(0, 5).text() == "LAST"


def test_register_panel_validates_runtime_edits_and_supports_copy():
    """Edit Ready-state register values through strict decimal and hex columns."""

    _app()
    debugger = configured_debugger("nop")
    panel = DebuggerRegisterPanel(debugger)
    panel.refresh()
    row = next(index for index in range(panel.rowCount()) if panel.item(index, 0).text() == "t0")

    assert panel.columnCount() == 3
    assert panel.horizontalHeaderItem(0).text() == "Reg"
    assert panel.maximumWidth() == DEBUGGER_LAYOUT.REGISTER_PANEL_MAX_WIDTH
    assert panel.minimumWidth() == 0
    assert panel.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
    panel.resize(DEBUGGER_LAYOUT.REGISTER_PANEL_MAX_WIDTH, 400)
    panel.show()
    QApplication.processEvents()
    panel._resize_columns()
    assert panel.columnWidth(0) == 55
    assert panel.columnWidth(1) >= 130
    assert panel.columnWidth(2) >= 155
    assert _content_to_scrollbar_gap(panel) == DEBUGGER_LAYOUT.TABLE_SCROLLBAR_GAP
    assert panel.item(0, 0).textAlignment() == Qt.AlignCenter
    assert all(panel.item(index, 0).text() != "zero" for index in range(panel.rowCount()))
    hex_editor = panel.itemDelegateForColumn(1).createEditor(panel, None, None)
    decimal_editor = panel.itemDelegateForColumn(2).createEditor(panel, None, None)
    assert hex_editor.validator().validate("0xFF", 4)[0] == QValidator.Acceptable
    assert hex_editor.validator().validate("GG", 2)[0] == QValidator.Invalid
    assert decimal_editor.validator().validate("255", 3)[0] == QValidator.Acceptable
    assert decimal_editor.validator().validate("FF", 2)[0] == QValidator.Invalid

    panel.item(row, 1).setText("FF")
    assert debugger.registers.read("t0") == 0xFF
    assert panel.item(row, 2).text() == "255"
    panel.item(row, 2).setText("42")
    assert debugger.registers.read("t0") == 42
    assert panel.item(row, 1).text() == "0x0000002A"
    debugger.step()
    assert debugger.registers.read("t0") == 42
    panel.setCurrentItem(panel.item(row, 2))
    QApplication.sendEvent(panel, QKeyEvent(QEvent.KeyPress, Qt.Key_C, Qt.ControlModifier))
    assert QApplication.clipboard().text() == "42"


def test_debug_log_highlights_execution_and_every_hexadecimal_value():
    """Color Execution and all `0x` values with their established syntax colors."""

    _app()
    document = QTextDocument(
        "Execution [0x80000000]: Write 0x801FFF90\n"
        "Memory [0x801FFF90]: Read memory\n"
        "Info: Breakpoint Ignored Import"
    )
    highlighter = DebuggerLogHighlighter(document)
    highlighter.rehighlight()
    colors = set()
    block = document.firstBlock()
    while block.isValid():
        colors.update(
            item.format.foreground().color().name().upper()
            for item in block.layout().formats()
        )
        block = block.next()
    assert "#41C1EC" in colors
    assert "#AF57DF" in colors
    assert "#62C6A1" in colors
    assert "#F4A261" in colors
    assert "#C9A27E" in colors
    assert "#F0C75E" in colors


def test_memory_grid_uses_four_bounded_cells_and_selected_block_summary():
    """Keep each editable memory cell fixed to four bytes without displacement."""

    _app()
    debugger = configured_debugger("nop")
    view = DebuggerMemoryView(debugger, debugger._image)
    view.resize(900, 400)
    view.show()
    QApplication.processEvents()

    assert view.table.columnCount() == 5
    assert view.table.horizontalHeaderItem(1).text() == "00 01 02 03"
    assert view.selection.text().startswith("Block:")
    assert view.search.placeholderText() == "Search Address"
    assert view.search.minimumWidth() == DEBUGGER_LAYOUT.MEMORY_SEARCH_MIN_WIDTH
    assert view.search._timer.interval() == DEBUGGER_LAYOUT.FILTER_DEBOUNCE_MS
    assert view.table.item(0, 0).foreground().color().name().upper() == "#62C6A1"
    assert (
        _content_to_scrollbar_gap(view.table)
        == DEBUGGER_LAYOUT.TABLE_SCROLLBAR_GAP
    )
    view.table.item(0, 1).setText("AA")
    assert debugger.read_memory(BASE, 4) == bytes.fromhex("AA 00 00 00")
    cell = view.table.item(0, 1)
    before = debugger.read_memory(BASE, 4)
    view._paste("01 02 03 04 05", (cell,))
    assert debugger.read_memory(BASE, 4) == before
    view._paste("11 22", (view.table.item(0, 1),))
    assert debugger.read_memory(BASE, 4) == bytes.fromhex("11 22 00 00")
    view.navigate(f"{BASE + 1:X}")
    assert f"0x{BASE + 1:08X} - 0x{BASE + 1:08X}" in view.selection.text()
    assert "Bytes: 1 (0x1)" in view.selection.text()
    view.navigate(f"{debugger._image.end:X}")
    out_of_range = next(
        item
        for row in range(view.table.rowCount())
        for column in range(1, view.table.columnCount())
        if (item := view.table.item(row, column)).text() == "Out Of Range"
    )
    assert out_of_range.foreground().color().name().upper() == "#DC143C"


def test_lower_tabs_remove_zones_filter_contextually_and_keep_psx_addresses():
    """Expose four aligned tabs and route full-width PSX addresses safely."""

    _app()
    debugger = configured_debugger("nop")
    tabs = DebuggerLowerTabs(debugger, debugger._image)
    tabs.resize(900, 400)
    tabs.show()
    QApplication.processEvents()

    assert tabs.count() == 4
    assert [tabs.tabText(index) for index in range(tabs.count())] == [
        "Stack View",
        "Memory View",
        "Breakpoints",
        "Debug Log",
    ]
    assert tabs.stack.columnCount() == 4
    assert tabs.stack.horizontalHeaderItem(2).text() == "Value (Hex)"
    assert tabs.stack.horizontalHeaderItem(3).text() == "Value (Dec)"
    tabs.stack.resize(900, 300)
    tabs.stack._resize_columns()
    assert all(
        tabs.stack.columnWidth(column) >= minimum
        for column, minimum in enumerate(DEBUGGER_LAYOUT.STACK_COLUMN_MINIMUMS)
    )
    assert (
        _content_to_scrollbar_gap(tabs.stack)
        == DEBUGGER_LAYOUT.TABLE_SCROLLBAR_GAP
    )
    tabs.setCurrentWidget(tabs.memory)
    assert not tabs.filter.isHidden()
    assert not tabs.filter.follow.isHidden()
    assert tabs.filter.search.isHidden()
    tabs.filter.follow_write.setChecked(True)
    assert tabs.memory._follow_writes
    assert not tabs.memory._follow_reads
    tabs.filter.follow_read.setChecked(True)
    assert tabs.memory._follow_reads
    tabs.setCurrentWidget(tabs.breakpoints)
    QApplication.processEvents()
    assert tabs.filter.isHidden()
    assert tabs.breakpoints.search.placeholderText() == "Search Breakpoint"
    assert (
        tabs.breakpoints.address.validator().validate("GG", 2)[0]
        == QValidator.Invalid
    )
    tabs.breakpoints.address.setText("80000000")
    tabs.breakpoints.address.returnPressed.emit()
    assert tabs.breakpoints.table.columnCount() == 4
    assert tabs.breakpoints.table.horizontalHeaderItem(1).text() == "Name"
    assert tabs.breakpoints.table.columnWidth(1) >= 180
    assert (
        _content_to_scrollbar_gap(tabs.breakpoints.table)
        == DEBUGGER_LAYOUT.TABLE_SCROLLBAR_GAP
    )
    name_delegate = tabs.breakpoints.table.itemDelegateForColumn(1)
    assert isinstance(name_delegate, BreakpointNameDelegate)
    name_editor = name_delegate.createEditor(tabs.breakpoints.table, None, None)
    assert name_editor.validator().validate("1invalid", 8)[0] == QValidator.Invalid
    assert name_editor.validator().validate("entry_point", 11)[0] == QValidator.Acceptable
    tabs.breakpoints.table.item(0, 1).setText("entry_point")
    assert debugger.breakpoints[0].name == "entry_point"
    tabs.breakpoints.set_filter("entry")
    assert not tabs.breakpoints.table.isRowHidden(0)
    tabs.breakpoints.set_filter("other")
    assert tabs.breakpoints.table.isRowHidden(0)
    tabs.breakpoints.set_filter("0x8000")
    assert not tabs.breakpoints.table.isRowHidden(0)
    delegate = tabs.breakpoints.table.itemDelegateForColumn(2)
    assert isinstance(delegate, SyntaxCellDelegate)
    assert delegate._highlighter_type is InstructionHighlighter
    navigated = []
    tabs.navigateRequested.connect(navigated.append)
    tabs.breakpoints._navigate_row(0, 0)
    assert navigated == [0x80000000]
    tabs.setCurrentWidget(tabs.log)
    tabs.resize(900, 300)
    QApplication.processEvents()
    assert tabs.filter.search.placeholderText() == "Search Log"
    assert tabs.filter.height() == tabs.tabBar().height()
    assert tabs.filter.search.height() == tabs.tabBar().height()
    assert tabs.log._clear_action.shortcut().toString() == "Ctrl+L"
    tabs.log._clear_action.trigger()
    assert debugger.events == ()
    debugger.record_event("Info", "alpha")
    debugger.record_event("Info", "beta")
    debugger._events.append(
        DebuggerEvent("Info", f"Breakpoint reached at 0x{BASE:08X}.", BASE)
    )
    tabs.log.refresh()
    assert "Info [" not in tabs.log.output.toPlainText()
    tabs.log.set_filter("alpha")
    assert "alpha" in tabs.log.output.toPlainText()
    assert "beta" not in tabs.log.output.toPlainText()


def test_debugger_toolbar_has_config_without_redundant_tooltips():
    """Keep action labels and shortcuts while suppressing toolbar tooltips."""

    app = _app()
    actions = DebuggerActions(app)
    bar = DebuggerActionBar(actions)

    assert actions.config.shortcut().toString() == "F11"
    assert actions.config.text() == "Config (F11)"
    buttons = bar.findChildren(QToolButton)
    assert all(
        button.event(QHelpEvent(QEvent.ToolTip, QPoint(), QPoint()))
        for button in buttons
    )
    dialog = DebuggerConfigDialog()
    assert dialog.interval.placeholderText() == "Interval (ms)"
    assert dialog.interval.validator().validate("2000", 4)[0] == QValidator.Acceptable
    assert dialog.interval.validator().validate("60001", 5)[0] != QValidator.Acceptable


def test_debugger_layout_keeps_registers_beside_both_left_panels(tmp_path):
    """Place instructions above lower tabs and registers across the full height."""

    app = _app()
    debugger = configured_debugger("nop")
    bundle = DebuggerSessionBundle(
        debugger,
        parse_debugger_directives(
            [f"* virtual_memory_range 0x{debugger._image.start:X} 0x{debugger._image.end:X}"]
        ),
        (),
        debugger._image,
    )
    window = DebuggerWindow(
        bundle,
        DebuggerActions(app),
        DebuggerWindowStateRepository(tmp_path / "debugger.json"),
        "test",
    )

    assert window.panels.horizontal.widget(0) is window.panels.vertical
    assert window.panels.horizontal.widget(1) is window.panels.registers
    assert window.panels.vertical.widget(0) is window.panels.instructions
    assert window.panels.vertical.widget(1) is window.panels.lower
    assert window.panels.horizontal.isCollapsible(1)
    window.close()
