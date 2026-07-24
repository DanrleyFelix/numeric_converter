"""Memory-grid navigation, editing and bounded paste behavior."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem

from src.core.debugger.models.session import (
    DebuggerError,
    DebuggerErrorCode,
    DebuggerSessionState,
)
from src.presentation.ui.components.debugger.panels.memory.code.disassembly import (
    refresh_memory_disassembly,
)
from src.presentation.ui.components.debugger.panels.memory.grid.formatter import (
    memory_cell_data,
    memory_paste_cells,
)


class DebuggerMemoryEditingMixin:
    """Apply address navigation and fixed-capacity memory changes."""

    def navigate(self, text: str) -> None:
        """Navigate to a hexadecimal address supplied by the shared filter."""

        try:
            value = int(text, 0 if text.lower().startswith("0x") else 16)
        except ValueError:
            value = -1
        if not self._image.contains(value):
            error = DebuggerError(
                DebuggerErrorCode.INVALID_MEMORY,
                f"Memory address 0x{value & 0xFFFFFFFF:08X} is outside the debugger image.",
            )
            self.errorRaised.emit(error.message)
            return
        self._start = self._aligned_start(value)
        self.refresh()
        self.table.clearSelection()
        offset = value - self._start
        item = self.table.item(offset // 16, offset % 16 // 4 + 1)
        if item is not None:
            item.setSelected(True)
        self._show_selection(value, value)

    def set_follow_writes(self, enabled: bool) -> None:
        """Enable or disable following the latest memory write."""

        self._follow_writes = enabled
        if self._debugger.state != DebuggerSessionState.RUNNING:
            self.refresh()

    def set_follow_reads(self, enabled: bool) -> None:
        """Enable or disable following the latest memory read."""

        self._follow_reads = enabled
        if self._debugger.state != DebuggerSessionState.RUNNING:
            self.refresh()

    def _edit_cell(self, item: QTableWidgetItem) -> None:
        """Normalize one edited cell and write exactly four bytes."""

        if self._refreshing or item.column() == 0:
            return
        if self._debugger.state == DebuggerSessionState.RUNNING:
            self.refresh()
            return
        data = memory_cell_data(item.text())
        if data is None or not self._write_cell(int(item.data(Qt.UserRole)), data):
            self.refresh()
            return
        self.refresh()

    def _paste(self, text: str, selected: tuple[QTableWidgetItem, ...]) -> None:
        """Write clipboard bytes only inside the selected cell capacity."""

        cells = memory_paste_cells(text, len(selected))
        if cells is None or self._debugger.state == DebuggerSessionState.RUNNING:
            return
        for item, data in zip(selected, cells):
            if not self._write_cell(int(item.data(Qt.UserRole)), data):
                break
        self.refresh()

    def _write_cell(self, address: int, data: bytes) -> bool:
        """Write one valid cell and refresh affected disassembly metadata."""

        if not self._image.contains(address, len(data)):
            return False
        self._debugger.write_memory(address, data)
        refresh_memory_disassembly(
            self._debugger, self._codec, self._image, address, len(data)
        )
        return True
