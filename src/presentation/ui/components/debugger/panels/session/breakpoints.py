"""Breakpoint entry and filtered metadata table."""

from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHeaderView,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.core.debugger.contracts.base import BWDebugger
from src.presentation.ui.components.binary_workbench.editor.highlighter_colors import (
    psx_mips_required_highlight_color,
)
from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT
from src.presentation.ui.components.debugger.constants.texts import (
    BREAKPOINT_ADDRESS_PLACEHOLDER,
    BREAKPOINT_HEADERS,
)
from src.presentation.ui.components.debugger.panels.instruction.highlighting import (
    instruction_cell_delegate,
)
from src.presentation.ui.components.debugger.panels.session.breakpoint.context_menu import (
    show_breakpoint_menu,
)
from src.presentation.ui.components.debugger.panels.session.breakpoint.presentation import (
    breakpoint_status,
    breakpoint_status_color,
    resize_breakpoint_columns,
)


class DebuggerBreakpointsView(QWidget):
    """Manage breakpoint metadata through Enter, filtering and context actions."""

    navigateRequested = Signal(object)

    def __init__(self, debugger: BWDebugger, parent=None) -> None:
        """Create a joined address entry and compact breakpoint table."""

        super().__init__(parent)
        self._debugger = debugger
        self._filter = ""
        self.address = QLineEdit(self)
        self.address.setObjectName("debugger-breakpoint-input")
        self.address.setPlaceholderText(BREAKPOINT_ADDRESS_PLACEHOLDER)
        self.address.setFixedHeight(DEBUGGER_LAYOUT.BREAKPOINT_ENTRY_HEIGHT)
        self.address.returnPressed.connect(self._add)
        self.table = QTableWidget(self)
        self.table.setObjectName("debugger-breakpoints-table")
        self.table.setColumnCount(len(BREAKPOINT_HEADERS))
        self.table.setHorizontalHeaderLabels(BREAKPOINT_HEADERS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setItemDelegateForColumn(1, instruction_cell_delegate(self.table))
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(
            DEBUGGER_LAYOUT.LOWER_TABLE_ROW_HEIGHT
        )
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        self.table.cellDoubleClicked.connect(self._navigate_row)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.address)
        layout.addWidget(self.table)
        self.refresh()

    def refresh(self) -> None:
        """Render breakpoint address, instruction and effective state."""

        breakpoints = self._debugger.breakpoints
        self.table.setRowCount(len(breakpoints))
        for row, breakpoint in enumerate(breakpoints):
            status = breakpoint_status(self._debugger, breakpoint)
            values = (
                f"0x{breakpoint.address:08X}",
                breakpoint.instruction,
                status,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setData(Qt.UserRole, breakpoint.address)
                item.setTextAlignment(Qt.AlignCenter)
                if column == 0:
                    item.setForeground(
                        QColor(psx_mips_required_highlight_color("hex"))
                    )
                elif column == 2:
                    item.setForeground(QColor(breakpoint_status_color(status)))
                self.table.setItem(row, column, item)
            self.table.setRowHidden(
                row, bool(self._filter and self._filter not in values[0].casefold())
            )
        resize_breakpoint_columns(self.table)

    def set_filter(self, text: str) -> None:
        """Filter visible breakpoints by formatted address characters."""

        self._filter = text.strip().casefold()
        self.refresh()

    def set_entry_width(self, width: int) -> None:
        """Match the address-entry width to the complete tab strip."""

        self.address.setFixedWidth(max(1, width))

    def _add(self) -> None:
        """Add the entered address when Enter is pressed."""

        try:
            text = self.address.text().strip()
            address = int(text, 0 if text.lower().startswith("0x") else 16)
        except ValueError:
            return
        self._debugger.add_breakpoint(address)
        self.address.clear()
        self.refresh()

    def _context_menu(self, position) -> None:
        """Offer standard styled breakpoint operations."""

        show_breakpoint_menu(self, position)

    def _navigate_row(self, row: int, _column: int) -> None:
        """Navigate to a double-clicked breakpoint without integer narrowing."""

        self.navigateRequested.emit(self.table.item(row, 0).data(Qt.UserRole))
