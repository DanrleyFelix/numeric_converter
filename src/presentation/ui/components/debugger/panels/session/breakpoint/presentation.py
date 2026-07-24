"""Breakpoint state labels, colors and column sizing."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QLineEdit,
    QStyledItemDelegate,
    QTableWidgetItem,
)

from src.core.debugger.models.session import DebuggerSessionState
from src.presentation.ui.components.binary_workbench.editor.highlighter_colors import (
    psx_mips_required_highlight_color,
)
from src.presentation.ui.components.binary_workbench.input_validators import (
    set_python_identifier_validator,
)
from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT
from src.presentation.ui.components.debugger.panels.table.editing import (
    fill_cell_editor,
    prepare_cell_editor,
)
from src.presentation.ui.helpers.load_qss import THEME_TOKENS


class BreakpointNameDelegate(QStyledItemDelegate):
    """Edit breakpoint names with the Binary Workbench symbol validator."""

    def createEditor(self, parent, option, index):
        """Create a symbol-compatible line editor for one Name cell."""

        editor = prepare_cell_editor(QLineEdit(parent))
        set_python_identifier_validator(editor)
        return editor

    def updateEditorGeometry(self, editor, option, _index) -> None:
        """Keep the breakpoint name editor equal to its complete cell."""

        fill_cell_editor(editor, option)


def render_breakpoint_rows(view) -> None:
    """Render breakpoint metadata and apply the active address/name filter."""

    breakpoints = view._debugger.breakpoints
    view._refreshing = True
    try:
        view.table.setRowCount(len(breakpoints))
        for row, breakpoint in enumerate(breakpoints):
            status = breakpoint_status(view._debugger, breakpoint)
            values = (
                f"0x{breakpoint.address:08X}",
                breakpoint.name,
                breakpoint.instruction,
                status,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column != DEBUGGER_LAYOUT.BREAKPOINT_NAME_COLUMN:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setData(Qt.UserRole, breakpoint.address)
                item.setTextAlignment(Qt.AlignCenter)
                if column == 0:
                    item.setForeground(QColor(psx_mips_required_highlight_color("hex")))
                elif column == 3:
                    item.setForeground(QColor(breakpoint_status_color(status)))
                view.table.setItem(row, column, item)
            target = values[0] if view._filter.startswith("0x") else breakpoint.name
            view.table.setRowHidden(
                row, bool(view._filter and view._filter not in target.casefold())
            )
    finally:
        view._refreshing = False
    view.fit_columns()


def breakpoint_status(debugger, breakpoint) -> str:
    """Return Enabled, Disabled, Triggered or Invalid."""

    if not breakpoint.valid:
        return "Invalid"
    if (
        breakpoint.enabled
        and debugger.state == DebuggerSessionState.PAUSED
        and debugger.pc == breakpoint.address
    ):
        return "Triggered"
    return "Enabled" if breakpoint.enabled else "Disabled"


def breakpoint_status_color(status: str) -> str:
    """Return the established state color for one breakpoint status."""

    if status == "Enabled":
        return THEME_TOKENS["text-success"]
    if status == "Triggered":
        return THEME_TOKENS["text-warning"]
    return THEME_TOKENS["text-danger"]
