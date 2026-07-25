"""Breakpoint state labels, colors and column sizing."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QLineEdit,
    QStyledItemDelegate,
    QTableWidgetItem,
)

from src.core.debugger.breakpoints.types import (
    ADDRESS_BREAKPOINT_TYPE_CHOICES,
    REGISTER_BREAKPOINT_TYPE,
)
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


class BreakpointTypeDelegate(QStyledItemDelegate):
    """Edit address breakpoint types through supported combinations only."""

    def createEditor(self, parent, option, index):
        """Create a pointer-enabled selector containing no synthetic `all` type."""

        editor = QComboBox(parent)
        editor.setCursor(Qt.PointingHandCursor)
        editor.addItems(ADDRESS_BREAKPOINT_TYPE_CHOICES)
        return editor

    def setEditorData(self, editor, index) -> None:
        """Select the breakpoint type currently stored by the model."""

        editor.setCurrentText(str(index.data() or "execution"))

    def setModelData(self, editor, model, index) -> None:
        """Commit the selected canonical type expression."""

        model.setData(index, editor.currentText())

    def updateEditorGeometry(self, editor, option, _index) -> None:
        """Keep the type selector equal to its complete cell."""

        fill_cell_editor(editor, option)


def render_breakpoint_rows(view) -> None:
    """Render typed breakpoint metadata and apply address/name filtering."""

    breakpoints = view._debugger.breakpoints
    view._refreshing = True
    try:
        view.table.setRowCount(len(breakpoints))
        for row, breakpoint in enumerate(breakpoints):
            status = breakpoint_status(breakpoint)
            instruction = (
                breakpoint.hit_instruction
                if breakpoint.breakpoint_type == REGISTER_BREAKPOINT_TYPE
                and breakpoint.hit_instruction
                else breakpoint.instruction
            )
            values = (
                breakpoint.breakpoint_type,
                breakpoint.where,
                breakpoint.name,
                instruction,
                status,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                editable = column == DEBUGGER_LAYOUT.BREAKPOINT_NAME_COLUMN or (
                    column == DEBUGGER_LAYOUT.BREAKPOINT_TYPE_COLUMN
                    and breakpoint.address is not None
                )
                if not editable:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setData(Qt.UserRole, breakpoint.identifier)
                item.setData(Qt.UserRole + 1, breakpoint.address)
                item.setTextAlignment(Qt.AlignCenter)
                if (
                    column == DEBUGGER_LAYOUT.BREAKPOINT_WHERE_COLUMN
                    and breakpoint.address is not None
                ):
                    item.setForeground(QColor(psx_mips_required_highlight_color("hex")))
                elif column == DEBUGGER_LAYOUT.BREAKPOINT_STATUS_COLUMN:
                    item.setForeground(QColor(breakpoint_status_color(status)))
                view.table.setItem(row, column, item)
            target = breakpoint.where if view._filter.startswith("0x") else breakpoint.name
            view.table.setRowHidden(
                row, bool(view._filter and view._filter not in target.casefold())
            )
    finally:
        view._refreshing = False
    view.fit_columns()


def breakpoint_status(breakpoint) -> str:
    """Return Enabled, Disabled, Triggered or Invalid."""

    if not breakpoint.valid:
        return "Invalid"
    if breakpoint.enabled and breakpoint.triggered:
        return "Triggered"
    return "Enabled" if breakpoint.enabled else "Disabled"


def breakpoint_status_color(status: str) -> str:
    """Return the established state color for one breakpoint status."""

    if status == "Enabled":
        return THEME_TOKENS["text-success"]
    if status == "Triggered":
        return THEME_TOKENS["text-warning"]
    return THEME_TOKENS["text-danger"]
