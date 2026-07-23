from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem

from src.core.debugger.memory.image import DebuggerMemoryImage
from src.presentation.ui.components.debugger.constants.texts import ZONE_HEADERS


class DebuggerZonesView(QTableWidget):
    """Display immutable virtual memory zones produced by session construction."""

    def __init__(self, image: DebuggerMemoryImage, parent=None) -> None:
        """Create and populate the virtual-memory zone table."""

        super().__init__(parent)
        self.setObjectName("debugger-zones-table")
        self.setColumnCount(len(ZONE_HEADERS))
        self.setHorizontalHeaderLabels(ZONE_HEADERS)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.verticalHeader().hide()
        self.setRowCount(len(image.zones))
        for row, zone in enumerate(image.zones):
            values = (
                f"0x{zone.start:08X}",
                f"0x{zone.end:08X}",
                str(zone.size),
                zone.origin,
                zone.status,
                str(zone.loaded_bytes),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.setItem(row, column, item)
