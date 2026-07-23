"""Editable debugger memory grid with fixed four-byte cells."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from src.core.binary_workbench.codec_registry import binary_workbench_codec_for
from src.core.debugger.contracts.base import BWDebugger
from src.core.debugger.memory.image import DebuggerMemoryImage
from src.presentation.ui.components.debugger.constants.texts import (
    MEMORY_SELECTION_EMPTY,
)
from src.presentation.ui.components.debugger.panels.memory.grid_view.editing import (
    DebuggerMemoryEditingMixin,
)
from src.presentation.ui.components.debugger.panels.memory.grid_view.rendering import (
    DebuggerMemoryRenderingMixin,
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
        self._follow_access = False
        self._refreshing = False
        self.table = self._create_table()
        self.selection = QLabel(MEMORY_SELECTION_EMPTY, self)
        self.selection.setObjectName("debugger-memory-selection")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.table)
        layout.addWidget(self.selection)
        self.refresh()
