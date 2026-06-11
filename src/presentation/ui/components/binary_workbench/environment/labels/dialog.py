from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLineEdit, QScrollArea, QVBoxLayout, QWidget

from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_widgets import (
    symbol_button,
    symbol_field,
    symbol_input,
)


class BinaryWorkbenchLabelsDialog(QDialog):
    goToRequested = Signal(int)

    def __init__(self, labels: dict[str, str], parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("workspace-table-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.LABELS)
        self.setMinimumSize(
            BINARY_WORKBENCH_LAYOUT.SYMBOLS_DIALOG_MIN_WIDTH,
            BINARY_WORKBENCH_LAYOUT.FILE_DIALOG_MIN_HEIGHT,
        )
        self.resize(BINARY_WORKBENCH_LAYOUT.SYMBOLS_DIALOG_WIDTH, BINARY_WORKBENCH_LAYOUT.FILE_DIALOG_HEIGHT)
        self._rows: list[tuple[QWidget, str, str]] = []
        self._build_dialog(labels)

    def _build_dialog(self, labels: dict[str, str]) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 30, 20, 20)
        shell = QFrame(self)
        shell.setObjectName("workspace-table-shell")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(20, 20, 20, 16)
        shell_layout.setSpacing(12)
        self.filter_input = symbol_input(
            BINARY_WORKBENCH_TEXT.FILTER,
            shell,
            "",
            BINARY_WORKBENCH_LAYOUT.LABELS_FILTER_WIDTH,
        )
        self.filter_input.textChanged.connect(self._apply_filter)
        shell_layout.addWidget(self.filter_input, 0, Qt.AlignLeft)
        self._build_body(shell, shell_layout)
        for name, offset in sorted(labels.items(), key=lambda item: int(item[1], 0)):
            self._append_row(name, offset)
        layout.addWidget(shell, 1)

    def _build_body(self, shell: QWidget, parent: QVBoxLayout) -> None:
        self.scroll = QScrollArea(shell)
        self.scroll.setObjectName("workspace-table-body-scroll")
        self.scroll.verticalScrollBar().setObjectName("workspace-table-scrollbar")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.body = QWidget(self.scroll)
        self.body.setObjectName("workspace-table-body")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 10, 0, 10)
        self.body_layout.setSpacing(10)
        self.body_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.body)
        parent.addWidget(self.scroll, 1)

    def _append_row(self, name: str, offset: str) -> None:
        row = QWidget(self.body)
        row.setObjectName("workspace-row")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        name_edit = _readonly_input(BINARY_WORKBENCH_TEXT.LABEL_NAME, row, name)
        offset_edit = _readonly_input(BINARY_WORKBENCH_TEXT.OFFSET, row, offset)
        go_to = symbol_button(BINARY_WORKBENCH_TEXT.GO_TO, "preferences-ok", row)
        go_to.setFixedSize(BINARY_WORKBENCH_LAYOUT.SYMBOL_ACTION_WIDTH, BINARY_WORKBENCH_LAYOUT.SYMBOL_INPUT_HEIGHT)
        go_to.clicked.connect(lambda: self._go_to(offset))
        layout.addWidget(symbol_field(BINARY_WORKBENCH_TEXT.LABEL_NAME, name_edit), 0)
        layout.addWidget(symbol_field(BINARY_WORKBENCH_TEXT.OFFSET, offset_edit), 0)
        layout.addWidget(go_to, 0, Qt.AlignBottom)
        self._rows.append((row, name, offset))
        self.body_layout.addWidget(row, 0, Qt.AlignLeft)

    def _apply_filter(self) -> None:
        query = self.filter_input.text().strip().lower()
        for row, name, offset in self._rows:
            row.setVisible(not query or query in f"{name} {offset}".lower())

    def _go_to(self, offset: str) -> None:
        self.goToRequested.emit(int(offset, 0))


def _readonly_input(placeholder: str, parent: QWidget, value: str) -> QLineEdit:
    editor = symbol_input(placeholder, parent, value, BINARY_WORKBENCH_LAYOUT.LBA_FIELD_WIDTH)
    editor.setReadOnly(True)
    return editor
