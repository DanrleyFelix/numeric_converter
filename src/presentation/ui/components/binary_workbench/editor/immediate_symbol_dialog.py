from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLineEdit, QVBoxLayout

from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_widgets import (
    symbol_button,
    symbol_field,
    symbol_input,
    symbol_label,
)


class ImmediateSymbolNameDialog(QDialog):
    def __init__(self, kind: str, value: str, parent=None) -> None:
        super().__init__(parent)
        self._kind = kind
        self._value = value
        self.setObjectName("workspace-table-dialog")
        self.setWindowTitle(kind)
        self._build_dialog()

    def symbol_name(self) -> str:
        return self.name_input.text().strip()

    def _build_dialog(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 30, 20, 20)
        shell = QFrame(self)
        shell.setObjectName("workspace-table-shell")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(20, 20, 20, 16)
        shell_layout.setSpacing(12)
        shell_layout.addWidget(symbol_label(self._kind, "workspace-table-title", shell))
        self.name_input = symbol_input(BINARY_WORKBENCH_TEXT.SYMBOL_NAME, shell, _default_name(self._kind, self._value))
        value_input = symbol_input(BINARY_WORKBENCH_TEXT.SYMBOL_VALUE, shell, self._value)
        value_input.setReadOnly(True)
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(symbol_field(BINARY_WORKBENCH_TEXT.SYMBOL_NAME, self.name_input))
        row.addWidget(symbol_field(BINARY_WORKBENCH_TEXT.SYMBOL_VALUE, value_input))
        shell_layout.addLayout(row)
        actions = QHBoxLayout()
        actions.setSpacing(14)
        ok = symbol_button("OK", "preferences-ok", shell)
        cancel = symbol_button("Cancel", "preferences-cancel", shell)
        for button in (ok, cancel):
            button.setFixedSize(BINARY_WORKBENCH_LAYOUT.SYMBOL_ACTION_WIDTH, BINARY_WORKBENCH_LAYOUT.SYMBOL_INPUT_HEIGHT)
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        actions.addWidget(ok, 0, Qt.AlignLeft)
        actions.addWidget(cancel, 0, Qt.AlignLeft)
        shell_layout.addLayout(actions)
        layout.addWidget(shell)


def _default_name(kind: str, value: str) -> str:
    prefix = "variable" if kind == BINARY_WORKBENCH_TEXT.VARIABLE_TARGET else "equate"
    cleaned = value.lower().replace("-", "minus_").replace("+", "").replace("0x", "")
    return f"{prefix}_{cleaned or 'value'}"
