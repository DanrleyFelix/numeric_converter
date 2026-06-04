from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFrame, QListWidget, QVBoxLayout

from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_widgets import (
    symbol_button,
    symbol_label,
)


class BinaryWorkbenchSymbolOffsetsDialog(QDialog):
    def __init__(self, name: str, offsets: list[str], parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("workspace-table-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.SYMBOL_OFFSETS)
        self.setMinimumWidth(BINARY_WORKBENCH_LAYOUT.SYMBOLS_DIALOG_MIN_WIDTH // 2)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 30, 20, 20)
        shell = QFrame(self)
        shell.setObjectName("workspace-table-shell")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(20, 20, 20, 16)
        shell_layout.setSpacing(12)
        shell_layout.addWidget(
            symbol_label(
                BINARY_WORKBENCH_TEXT.SYMBOL_OFFSETS_TITLE_TEMPLATE.format(name=name),
                "workspace-table-title",
                shell,
            )
        )
        self.offsets = QListWidget(shell)
        self.offsets.setObjectName("binary-workbench-search-results")
        self.offsets.setCursor(Qt.PointingHandCursor)
        self.offsets.setFocusPolicy(Qt.NoFocus)
        self.offsets.setMouseTracking(True)
        self.offsets.addItems(offsets or [BINARY_WORKBENCH_TEXT.SYMBOL_OFFSETS_EMPTY])
        shell_layout.addWidget(self.offsets)
        ok = symbol_button("OK", "preferences-ok", shell)
        ok.setFixedSize(
            BINARY_WORKBENCH_LAYOUT.SYMBOL_FIELD_WIDTH,
            BINARY_WORKBENCH_LAYOUT.SYMBOL_INPUT_HEIGHT,
        )
        ok.clicked.connect(self.accept)
        shell_layout.addWidget(ok, 0, Qt.AlignLeft)
        layout.addWidget(shell)
