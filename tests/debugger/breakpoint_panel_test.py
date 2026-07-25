import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QValidator
from PySide6.QtWidgets import QApplication, QFrame, QMenu, QPushButton

from src.presentation.ui.components.binary_workbench.editor.context_menu_icons import (
    use_white_menu_icons,
)
from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT
from src.presentation.ui.components.debugger.panels.register.breakpoint.dialog import (
    DebuggerRegisterBreakpointDialog,
)
from src.presentation.ui.components.debugger.panels.registers import (
    DebuggerRegisterPanel,
)
from src.presentation.ui.components.debugger.panels.tabs.widget import (
    DebuggerLowerTabs,
)
from helpers import BASE, configured_debugger

_APP = None


def _app() -> QApplication:
    """Return the shared application for breakpoint panel tests."""

    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


def test_register_panel_action_and_condition_dialog_create_register_breakpoint():
    """Expose Alt+B and create only a register condition with Config geometry."""

    _app()
    debugger = configured_debugger("addiu $s2, $zero, 2", "nop")
    registers = DebuggerRegisterPanel(debugger)
    registers.refresh()
    assert registers._add_breakpoint_action.text() == "Add Breakpoint"
    assert registers._add_breakpoint_action.shortcut().toString() == "Alt+B"
    assert not registers._add_breakpoint_action.icon().isNull()

    dialog = DebuggerRegisterBreakpointDialog(debugger, "s2")
    assert dialog.condition.width() == DEBUGGER_LAYOUT.CONFIG_FIELD_WIDTH
    assert dialog.layout().spacing() == DEBUGGER_LAYOUT.CONFIG_VERTICAL_SPACING
    confirm = next(
        button
        for button in dialog.findChildren(QPushButton)
        if button.text() == "Confirm"
    )
    assert confirm.width() == DEBUGGER_LAYOUT.CONFIG_CONFIRM_WIDTH
    dialog.condition.setText("$s2 == 0x2")
    dialog._accept_condition()

    breakpoint = debugger.breakpoints[0]
    assert dialog.result() == dialog.DialogCode.Accepted
    assert breakpoint.breakpoint_type == "register"
    assert breakpoint.where == "$s2 == 0x2"


def test_register_breakpoint_row_reveals_instruction_only_after_hit():
    """Render Type, WHERE and a centered dash until the condition fires."""

    _app()
    debugger = configured_debugger("addiu $s2, $zero, 2", "nop")
    debugger.add_register_breakpoint("$s2 == 0x2")
    tabs = DebuggerLowerTabs(debugger, debugger._image)
    tabs.breakpoints.refresh()
    table = tabs.breakpoints.table

    assert table.horizontalHeaderItem(0).text() == "Type"
    assert table.horizontalHeaderItem(1).text() == "WHERE"
    assert table.item(0, DEBUGGER_LAYOUT.BREAKPOINT_TYPE_COLUMN).text() == "reg"
    assert table.item(0, DEBUGGER_LAYOUT.BREAKPOINT_WHERE_COLUMN).text() == "$s2 == 0x2"
    instruction = table.item(0, DEBUGGER_LAYOUT.BREAKPOINT_INSTRUCTION_COLUMN)
    assert instruction.text() == "-"
    assert instruction.textAlignment() == Qt.AlignCenter
    assert (
        table.item(0, DEBUGGER_LAYOUT.BREAKPOINT_TYPE_COLUMN).flags()
        & Qt.ItemIsEditable
    )
    assert (
        table.item(0, DEBUGGER_LAYOUT.BREAKPOINT_WHERE_COLUMN).flags()
        & Qt.ItemIsEditable
    )
    where_delegate = table.itemDelegateForColumn(
        DEBUGGER_LAYOUT.BREAKPOINT_WHERE_COLUMN
    )
    where_index = table.model().index(
        0, DEBUGGER_LAYOUT.BREAKPOINT_WHERE_COLUMN
    )
    assert where_delegate.createEditor(table, None, where_index).validator() is None

    debugger.run(limit=10)
    tabs.breakpoints.refresh()

    assert (
        table.item(0, DEBUGGER_LAYOUT.BREAKPOINT_INSTRUCTION_COLUMN).text()
        == "addiu $s2, $zero, 2"
    )
    assert (
        table.item(0, DEBUGGER_LAYOUT.BREAKPOINT_STATUS_COLUMN).text()
        == "Triggered"
    )


def test_type_column_uses_compact_options_and_persists_canonical_order():
    """Offer compact combinations including reg and persist canonical order."""

    _app()
    debugger = configured_debugger("nop")
    debugger.add_breakpoint(BASE)
    tabs = DebuggerLowerTabs(debugger, debugger._image)
    table = tabs.breakpoints.table
    delegate = table.itemDelegateForColumn(
        DEBUGGER_LAYOUT.BREAKPOINT_TYPE_COLUMN
    )
    editor = delegate.createEditor(table, None, None)
    assert editor.view().frameShape() == QFrame.NoFrame
    choices = tuple(editor.itemText(index) for index in range(editor.count()))
    assert "all" not in choices
    assert "register" not in choices
    assert "reg" in choices
    assert "w | r | exec" in choices
    assert (
        DEBUGGER_LAYOUT.BREAKPOINT_COLUMN_MAXIMUMS[
            DEBUGGER_LAYOUT.BREAKPOINT_INSTRUCTION_COLUMN
        ]
        == 220
    )
    assert DEBUGGER_LAYOUT.BREAKPOINT_COLUMN_MAXIMUMS[
        DEBUGGER_LAYOUT.BREAKPOINT_NAME_COLUMN
    ] == 170
    assert table.columnWidth(DEBUGGER_LAYOUT.BREAKPOINT_TYPE_COLUMN) == 100
    where_delegate = table.itemDelegateForColumn(
        DEBUGGER_LAYOUT.BREAKPOINT_WHERE_COLUMN
    )
    where_index = table.model().index(
        0, DEBUGGER_LAYOUT.BREAKPOINT_WHERE_COLUMN
    )
    address_editor = where_delegate.createEditor(table, None, where_index)
    assert address_editor.validator().validate("GG", 2)[0] == QValidator.Invalid

    table.item(0, DEBUGGER_LAYOUT.BREAKPOINT_TYPE_COLUMN).setText(
        "r | w"
    )

    assert debugger.breakpoints[0].breakpoint_type == "write || read"


def test_instruction_context_menu_assigns_an_icon_to_every_action():
    """Keep every debugger context action aligned through standard menu icons."""

    _app()
    menu = QMenu()
    actions = tuple(
        menu.addAction(text)
        for text in (
            "Toggle Breakpoint",
            "Remove Breakpoint",
            "Copy Address",
            "Toggle IGNORED",
            "Enable",
            "Disable",
            "Remove",
            "Copy WHERE",
            "Go to Instruction",
        )
    )
    use_white_menu_icons(menu)
    assert all(not action.icon().isNull() for action in actions)
