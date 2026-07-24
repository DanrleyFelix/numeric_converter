"""Editable debugger memory grid with fixed four-byte cells."""

from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.core.binary_workbench.codec_registry import binary_workbench_codec_for
from src.core.debugger.contracts.base import BWDebugger
from src.core.debugger.memory.image import DebuggerMemoryImage
from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT
from src.presentation.ui.components.debugger.constants.texts import (
    MEMORY_ADDRESS_FILTER,
    MEMORY_SELECTION_EMPTY,
)
from src.presentation.ui.components.debugger.panels.memory.grid_view.editing import (
    DebuggerMemoryEditingMixin,
)
from src.presentation.ui.components.debugger.panels.memory.grid_view.rendering import (
    DebuggerMemoryRenderingMixin,
)
from src.presentation.ui.components.debugger.panels.tabs.filter_bar import (
    DebouncedSearchEdit,
)


class DebuggerMemoryView(
    DebuggerMemoryEditingMixin,
    DebuggerMemoryRenderingMixin,
    QWidget,
):
    """Inspect, select and edit volatile memory in sixteen-byte rows."""

    errorRaised = Signal(str)

    def __init__(self, debugger: BWDebugger, image: DebuggerMemoryImage, parent=None) -> None:
        """Create a four-column byte grid and selected-block summary."""

        super().__init__(parent)
        self._debugger = debugger
        self._image = image
        self._codec = binary_workbench_codec_for(debugger.architecture)
        self._start = image.start
        self._follow_writes = False
        self._follow_reads = False
        self._refreshing = False
        self.table = self._create_table()
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self.table.resize_columns)
        self.selection = QLabel(MEMORY_SELECTION_EMPTY, self)
        self.selection.setObjectName("debugger-memory-selection")
        self.search = DebouncedSearchEdit(MEMORY_ADDRESS_FILTER, self)
        self.search.setObjectName("debugger-memory-search")
        self.search.setMinimumWidth(DEBUGGER_LAYOUT.MEMORY_SEARCH_MIN_WIDTH)
        self.search.filterApplied.connect(self._search_address)
        footer = QWidget(self)
        footer.setObjectName("debugger-memory-footer")
        summary = QWidget(footer)
        summary.setObjectName("debugger-memory-summary")
        summary_layout = QHBoxLayout(summary)
        summary_layout.setContentsMargins(
            DEBUGGER_LAYOUT.MEMORY_FOOTER_LEFT_MARGIN, 0, 0, 0
        )
        summary_layout.addWidget(self.selection)
        summary_layout.addStretch()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(0)
        footer_layout.addWidget(summary, 1)
        footer_layout.addWidget(self.search)
        divider = QWidget(self)
        divider.setObjectName("debugger-memory-divider")
        divider.setFixedHeight(DEBUGGER_LAYOUT.PANEL_BORDER_WIDTH)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.table)
        layout.addWidget(divider)
        layout.addWidget(footer)
        self.refresh()

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Resize the byte columns once from the stable parent geometry."""

        super().resizeEvent(event)
        self._resize_timer.start(0)

    def _search_address(self, text: str) -> None:
        """Navigate when the debounced footer address is non-empty."""

        if text:
            self.navigate(text)
