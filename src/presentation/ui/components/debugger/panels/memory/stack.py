from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem

from src.core.debugger.contracts.base import BWDebugger
from src.core.debugger.memory.image import DebuggerMemoryImage
from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT
from src.presentation.ui.helpers.load_qss import THEME_TOKENS


class DebuggerStackView(QTableWidget):
    """Display stack-relative words using the backend-provided stack register."""

    def __init__(self, debugger: BWDebugger, image: DebuggerMemoryImage, parent=None) -> None:
        """Create a read-only stack table bound to the debugger register contract."""

        super().__init__(parent)
        self._debugger = debugger
        self._image = image
        self._snapshot: dict[int, bytes] = {}
        self.setObjectName("debugger-stack-table")
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(("Offset", "Address", "Value"))
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize(
            DEBUGGER_LAYOUT.LOWER_TABLE_ROW_HEIGHT
        )
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.refresh()

    def refresh(self) -> None:
        """Read stack words and highlight values changed since the prior refresh."""

        stack_name = self._debugger.registers.stack_register
        stack = self._debugger.registers.read(stack_name)
        self.setRowCount(DEBUGGER_LAYOUT.STACK_ROWS)
        current: dict[int, bytes] = {}
        for row in range(DEBUGGER_LAYOUT.STACK_ROWS):
            offset = (row - DEBUGGER_LAYOUT.STACK_ROWS // 2) * 4
            address = stack + offset
            data = self._word(address)
            changed = address in self._snapshot and self._snapshot[address] != data
            current[address] = data
            values = (
                f"{offset:+d}",
                f"0x{address:08X}",
                f"0x{int.from_bytes(data, 'little'):08X}" if data else "-",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setTextAlignment(Qt.AlignCenter)
                if changed:
                    item.setBackground(QColor(THEME_TOKENS["bg-state-success-soft"]))
                self.setItem(row, column, item)
        self._snapshot = current
        for column, adjustment in enumerate(DEBUGGER_LAYOUT.STACK_COLUMN_ADJUSTMENTS):
            self.resizeColumnToContents(column)
            if adjustment:
                self.setColumnWidth(column, self.columnWidth(column) + adjustment)

    def _word(self, address: int) -> bytes:
        """Read one complete stack word or return an out-of-range marker."""

        if not self._image.contains(address, 4):
            return b""
        return self._debugger.read_memory(address, 4)
