from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QListWidget, QListWidgetItem, QVBoxLayout

from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_widgets import symbol_label


class BinaryWorkbenchSymbolOffsetsDialog(QDialog):
    goToRequested = Signal(int)

    def __init__(self, name: str, offsets: list[str], parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("workspace-table-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.SYMBOL_OFFSETS)
        self.setMinimumWidth(BINARY_WORKBENCH_LAYOUT.SYMBOLS_DIALOG_MIN_WIDTH // 2)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 30, 20, 20)
        layout.setSpacing(12)
        title = symbol_label(name, "workspace-table-title", self)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        self.offsets = QListWidget(self)
        self.offsets.setObjectName("binary-workbench-symbol-offsets")
        self.offsets.setFocusPolicy(Qt.NoFocus)
        self.offsets.setMouseTracking(True)
        if offsets:
            self.offsets.setCursor(Qt.PointingHandCursor)
            self.offsets.addItems(offsets)
        else:
            self.offsets.setCursor(Qt.ArrowCursor)
            self.offsets.addItem(BINARY_WORKBENCH_TEXT.SYMBOL_OFFSETS_EMPTY)
            self.offsets.item(0).setFlags(Qt.NoItemFlags)
        self.offsets.itemClicked.connect(self._go_to_offset)
        layout.addWidget(self.offsets)

    def _go_to_offset(self, item: QListWidgetItem) -> None:
        if not item.flags() & Qt.ItemIsEnabled:
            return
        try:
            self.goToRequested.emit(int(item.text(), 0))
        except ValueError:
            return
