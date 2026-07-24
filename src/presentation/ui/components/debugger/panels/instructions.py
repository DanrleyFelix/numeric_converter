from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor, QResizeEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)

from src.core.debugger.contracts.base import BWDebugger
from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT
from src.presentation.ui.components.debugger.constants.texts import INSTRUCTION_HEADERS
from src.presentation.ui.components.debugger.panels.instruction.highlighting import (
    bytes_cell_delegate, instruction_cell_color, instruction_cell_delegate,
)
from src.presentation.ui.components.debugger.panels.instruction.context.menu import (
    show_instruction_menu,
)
from src.presentation.ui.components.debugger.panels.instruction.layout.sizing import (
    resize_instruction_columns,
)
from src.presentation.ui.components.debugger.panels.instruction.status import instruction_status
from src.presentation.ui.helpers.load_qss import THEME_TOKENS


class DebuggerInstructionPanel(QTableWidget):
    """Display mapped instructions and current execution status."""

    breakpointToggled = Signal(object)
    breakpointRemoved = Signal(object)
    ignoredToggled = Signal(object)

    def __init__(self, parent=None) -> None:
        """Create a read-only debugger instruction table."""

        super().__init__(parent)
        self.setObjectName("debugger-instructions")
        self.setColumnCount(len(INSTRUCTION_HEADERS))
        self.setHorizontalHeaderLabels(INSTRUCTION_HEADERS)
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(False)
        for column in (
            DEBUGGER_LAYOUT.RAW_INSTRUCTION_COLUMN,
            DEBUGGER_LAYOUT.INSTRUCTION_STATUS_COLUMN,
        ):
            header.setSectionResizeMode(column, QHeaderView.Fixed)
        self.setItemDelegateForColumn(2, bytes_cell_delegate(self))
        self.setItemDelegateForColumn(3, instruction_cell_delegate(self))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setCursor(Qt.PointingHandCursor)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._open_context_menu)
        self.cellClicked.connect(self._cell_clicked)
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize(DEBUGGER_LAYOUT.TABLE_ROW_HEIGHT)

    def refresh(self, debugger: BWDebugger, last_pc: int | None = None) -> None:
        """Render instructions and emphasize the current/previous program counter."""

        instructions = debugger.instructions
        self.setRowCount(len(instructions))
        current_pc = debugger.pc
        for row, instruction in enumerate(instructions):
            status = instruction_status(
                debugger,
                instruction.address,
                current_pc,
                last_pc,
                instruction.status,
            )
            values = (
                str(row + 1),
                f"0x{instruction.address:08X}",
                " ".join(f"{value:02X}" for value in instruction.data),
                instruction.raw_instruction,
                instruction.origin,
                status,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, f"0x{instruction.address:08X}")
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setTextAlignment(Qt.AlignCenter)
                color = instruction_cell_color(column, value)
                if color:
                    item.setForeground(QColor(color))
                if status == "ACTUAL":
                    item.setBackground(QColor(THEME_TOKENS["bg-control-checked-hover"]))
                elif status == "LAST":
                    item.setBackground(QColor(THEME_TOKENS["bg-menu-item-checked"]))
                self.setItem(row, column, item)
            if instruction.address == current_pc:
                self.scrollToItem(self.item(row, 1), QAbstractItemView.PositionAtCenter)
        self._resize_columns()

    def _resize_columns(self) -> None:
        """Resize flexible columns without accumulating width on refresh."""

        resize_instruction_columns(self)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Keep instruction columns attached to the vertical scrollbar."""

        super().resizeEvent(event)
        self._resize_columns()

    def navigate_to(self, address: int) -> None:
        """Select and center one exact instruction address when loaded."""

        for row in range(self.rowCount()):
            item = self.item(row, 1)
            if item is not None and int(item.data(Qt.UserRole), 0) == address:
                self.selectRow(row)
                self.scrollToItem(item, QAbstractItemView.PositionAtCenter)
                return

    def _toggle_breakpoint_row(self, row: int) -> None:
        """Request a breakpoint toggle from the instruction gutter."""

        item = self.item(row, 1)
        if item is not None:
            self.breakpointToggled.emit(int(item.data(Qt.UserRole), 0))

    def _cell_clicked(self, row: int, column: int) -> None:
        """Treat the first table column as the breakpoint gutter."""

        if column == 0:
            self._toggle_breakpoint_row(row)

    def _open_context_menu(self, position) -> None:
        """Open the standard instruction-row context actions."""

        show_instruction_menu(self, position)
