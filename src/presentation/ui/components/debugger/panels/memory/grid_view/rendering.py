"""Memory-grid construction, rendering and selection summary."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QTableWidgetItem

from src.presentation.ui.components.binary_workbench.editor.highlighter_colors import (
    psx_mips_required_highlight_color,
)
from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT
from src.presentation.ui.components.debugger.constants.texts import (
    MEMORY_OUT_OF_RANGE,
    MEMORY_SELECTION_EMPTY,
    MEMORY_SELECTION_TEMPLATE,
)
from src.presentation.ui.components.debugger.panels.memory.grid.formatter import (
    memory_cell_text,
)
from src.presentation.ui.components.debugger.panels.memory.grid.table import (
    DebuggerMemoryTable,
    HexBytesDelegate,
)
from src.presentation.ui.helpers.load_qss import THEME_TOKENS


class DebuggerMemoryRenderingMixin:
    """Render fixed memory cells and their inclusive selected range."""

    def _create_table(self) -> DebuggerMemoryTable:
        """Create the memory table with fixed offset groups."""

        table = DebuggerMemoryTable(self)
        table.setObjectName("debugger-memory-table")
        headers = ("Address",) + tuple(
            " ".join(f"{offset + index:02X}" for index in range(4))
            for offset in range(0, DEBUGGER_LAYOUT.MEMORY_BYTES_PER_ROW, 4)
        )
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.configure_column_layout()
        table.setSelectionMode(DebuggerMemoryTable.ExtendedSelection)
        table.setSelectionBehavior(DebuggerMemoryTable.SelectItems)
        table.setItemDelegate(HexBytesDelegate(table))
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.verticalHeader().hide()
        table.verticalHeader().setDefaultSectionSize(
            DEBUGGER_LAYOUT.LOWER_TABLE_ROW_HEIGHT
        )
        table.itemChanged.connect(self._edit_cell)
        table.itemSelectionChanged.connect(self._selection_changed)
        table.pasteRequested.connect(self._paste)
        return table

    def _render_row(self, row: int, address: int) -> None:
        """Render one address and four independent byte cells."""

        address_item = QTableWidgetItem(f"0x{address:08X}")
        address_item.setFlags(address_item.flags() & ~Qt.ItemIsEditable)
        address_item.setTextAlignment(Qt.AlignCenter)
        address_item.setForeground(
            QColor(psx_mips_required_highlight_color("hex"))
        )
        self.table.setItem(row, 0, address_item)
        for column in range(1, DEBUGGER_LAYOUT.MEMORY_BYTE_COLUMNS + 1):
            cell_address = address + (column - 1) * DEBUGGER_LAYOUT.MEMORY_BYTES_PER_CELL
            if self._image.contains(cell_address, DEBUGGER_LAYOUT.MEMORY_BYTES_PER_CELL):
                data = self._debugger.read_memory(
                    cell_address, DEBUGGER_LAYOUT.MEMORY_BYTES_PER_CELL
                )
                item = QTableWidgetItem(memory_cell_text(data))
            else:
                item = QTableWidgetItem(MEMORY_OUT_OF_RANGE)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setForeground(
                    QColor(THEME_TOKENS["text-debug-out-of-range"])
                )
            item.setData(Qt.UserRole, cell_address)
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, column, item)

    def _selection_changed(self) -> None:
        """Summarize the inclusive address block represented by selected cells."""

        addresses = [
            int(item.data(Qt.UserRole))
            for item in self.table.selectedItems()
            if item.column() > 0 and item.data(Qt.UserRole) is not None
        ]
        if not addresses:
            self.selection.setText(MEMORY_SELECTION_EMPTY)
            return
        self._show_selection(min(addresses), max(addresses) + 3)

    def _show_selection(self, start: int, end: int) -> None:
        """Display one inclusive block in decimal and hexadecimal sizes."""

        self.selection.setText(
            MEMORY_SELECTION_TEMPLATE.format(start=start, end=end, size=end - start + 1)
        )

    def _latest_access(self):
        """Return the newest enabled runtime read or write event."""

        operations = tuple(
            name
            for name, enabled in (
                ("Write ", self._follow_writes),
                ("Read ", self._follow_reads),
            )
            if enabled
        )
        if not operations:
            return None
        return next(
            (
                event
                for event in reversed(self._debugger.events)
                if event.level == "Memory"
                and event.message.startswith(operations)
            ),
            None,
        )
