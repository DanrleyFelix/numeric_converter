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
from src.presentation.ui.components.debugger.panels.tabs.widget import DebuggerLowerTabs
from src.presentation.ui.components.debugger.window import DebuggerWindow
from helpers import BASE, configured_debugger

_APP = None


def _app() -> QApplication:
    """Return the shared application for debugger panel tests."""

    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


def test_instruction_panel_uses_exec_status_width_limits_and_bytes_delegate():
    """Keep instruction columns readable and render repeated execution distinctly."""

    _app()
    debugger = configured_debugger("nop", "nop")
    debugger.statistics.executed[BASE] = 3
    panel = DebuggerInstructionPanel()
    panel.refresh(debugger, BASE)

    assert panel.item(0, 5).text() == "EXEC (3)"
    assert panel.item(0, 5).foreground().color().name().upper() == "#1E90FF"
    assert panel.columnWidth(3) == DEBUGGER_LAYOUT.RAW_INSTRUCTION_WIDTH
    assert panel.columnWidth(5) == DEBUGGER_LAYOUT.INSTRUCTION_STATUS_WIDTH
    assert not panel.horizontalHeader().stretchLastSection()
    assert panel.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
    delegate = panel.itemDelegateForColumn(2)
    assert isinstance(delegate, SyntaxCellDelegate)
    assert delegate._highlighter_type is BytesHighlighter
    debugger.statistics.executed.clear()
    panel.refresh(debugger)
    assert panel.item(0, 5).text() == "ACTUAL"
    assert panel.item(1, 5).text() == "READY"
    panel.refresh(debugger)
    assert panel.columnWidth(5) == DEBUGGER_LAYOUT.INSTRUCTION_STATUS_WIDTH
    debugger.pc = BASE + 4
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
    assert panel.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
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
        "Memory [0x801FFF90]: Read memory"
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


def test_memory_grid_uses_four_bounded_cells_and_selected_block_summary():
    """Keep each editable memory cell fixed to four bytes without displacement."""

    _app()
    debugger = configured_debugger("nop")
    view = DebuggerMemoryView(debugger, debugger._image)

    assert view.table.columnCount() == 5
    assert view.table.horizontalHeaderItem(1).text() == "00 01 02 03"
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


def test_lower_tabs_remove_zones_filter_contextually_and_keep_psx_addresses():
    """Expose four aligned tabs and route full-width PSX addresses safely."""

    _app()
    debugger = configured_debugger("nop")
    tabs = DebuggerLowerTabs(debugger, debugger._image)

    assert tabs.count() == 4
    assert [tabs.tabText(index) for index in range(tabs.count())] == [
        "Stack View",
        "Memory View",
        "Breakpoints",
        "Debug Log",
    ]
    assert tabs.stack.columnCount() == 3
    tabs.setCurrentWidget(tabs.memory)
    assert tabs.filter.search.placeholderText() == "Search Address"
    assert not tabs.filter.follow.isHidden()
    assert tabs.filter._timer.interval() == 2000
    tabs.setCurrentWidget(tabs.breakpoints)
    tabs.breakpoints.address.setText("80000000")
    tabs.breakpoints.address.returnPressed.emit()
    assert tabs.breakpoints.table.columnCount() == 3
    delegate = tabs.breakpoints.table.itemDelegateForColumn(1)
    assert isinstance(delegate, SyntaxCellDelegate)
    assert delegate._highlighter_type is InstructionHighlighter
    navigated = []
    tabs.navigateRequested.connect(navigated.append)
    tabs.breakpoints._navigate_row(0, 0)
    assert navigated == [0x80000000]
    assert tabs.log._clear_action.shortcut().toString() == "Ctrl+L"
    tabs.log._clear_action.trigger()
    assert debugger.events == ()
    debugger.record_event("Info", "alpha")
    debugger.record_event("Info", "beta")
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
    window.close()
