from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QDialog, QListWidget, QListWidgetItem, QVBoxLayout

from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_DIALOG_LAYOUT as ENVIRONMENT_LAYOUT,
)
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_widgets import symbol_label


class BinaryWorkbenchSymbolOffsetsDialog(QDialog):
    """Display navigable offsets for one symbol and one tab context."""

    goToRequested = Signal(int)

    def __init__(self, name: str, offsets: list[str], parent=None) -> None:
        """Create a snapshot view of the supplied offsets."""

        super().__init__(parent)
        self.setObjectName("workspace-table-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.SYMBOL_OFFSETS)
        self.setMinimumWidth(BINARY_WORKBENCH_LAYOUT.SYMBOLS_DIALOG_MIN_WIDTH // 2)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*ENVIRONMENT_LAYOUT.DIALOG_MARGINS)
        layout.setSpacing(ENVIRONMENT_LAYOUT.PANEL_SPACING)
        title = symbol_label(name, "workspace-table-title", self)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        self.offsets = QListWidget(self)
        self.offsets.setObjectName("binary-workbench-symbol-offsets")
        self.offsets.setFocusPolicy(Qt.NoFocus)
        self.offsets.setMouseTracking(True)
        self.offsets.setSpacing(0)
        self.offsets.setUniformItemSizes(True)
        self._set_offsets(offsets)
        self.offsets.itemClicked.connect(self._go_to_offset)
        layout.addWidget(self.offsets)

    def _go_to_offset(self, item: QListWidgetItem) -> None:
        """Navigate only when the clicked entry represents a valid offset."""

        if not item.flags() & Qt.ItemIsEnabled:
            return
        try:
            self.goToRequested.emit(int(item.text(), 0))
        except ValueError:
            return

    def mark_stale(self) -> None:
        """Invalidate displayed Global Offsets after the active tab changes."""

        self.offsets.clear()
        self.offsets.setCursor(Qt.ArrowCursor)
        self._append_item(BINARY_WORKBENCH_TEXT.SYMBOL_OFFSETS_STALE, enabled=False)

    def _set_offsets(self, offsets: list[str]) -> None:
        """Populate either navigable offsets or the established empty state."""

        if offsets:
            self.offsets.setCursor(Qt.PointingHandCursor)
            for offset in offsets:
                self._append_item(offset)
            return
        self.offsets.setCursor(Qt.ArrowCursor)
        self._append_item(BINARY_WORKBENCH_TEXT.SYMBOL_OFFSETS_EMPTY, enabled=False)

    def _append_item(self, text: str, *, enabled: bool = True) -> None:
        """Append one full-width row whose height is twice the active font."""

        item = QListWidgetItem(text)
        item.setSizeHint(QSize(0, self.offsets.fontMetrics().height() * 2))
        if not enabled:
            item.setFlags(Qt.NoItemFlags)
        self.offsets.addItem(item)
