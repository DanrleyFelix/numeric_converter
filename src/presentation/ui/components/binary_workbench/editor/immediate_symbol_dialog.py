from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QVBoxLayout

from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_widgets import (
    symbol_button,
    symbol_input,
)

SYMBOL_NAME_CLEANUP = re.compile(r"[^0-9a-z_]+")


class ImmediateSymbolNameDialog(QDialog):
    def __init__(self, kind: str, value: str, parent=None) -> None:
        super().__init__(parent)
        self._kind = kind
        self._value = value
        self.setObjectName("workspace-table-dialog")
        self.setWindowTitle(kind)
        self.setMaximumSize(
            BINARY_WORKBENCH_LAYOUT.IMMEDIATE_SYMBOL_DIALOG_MAX_WIDTH,
            BINARY_WORKBENCH_LAYOUT.IMMEDIATE_SYMBOL_DIALOG_MAX_HEIGHT,
        )
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
        field_width = BINARY_WORKBENCH_LAYOUT.IMMEDIATE_SYMBOL_FIELD_WIDTH
        self.name_input = symbol_input(
            BINARY_WORKBENCH_TEXT.SYMBOL_NAME,
            shell,
            _default_name(self._kind, self._value),
            field_width,
        )
        value_input = symbol_input(
            BINARY_WORKBENCH_TEXT.SYMBOL_VALUE,
            shell,
            self._value,
            field_width,
        )
        value_input.setReadOnly(True)
        row = QHBoxLayout()
        row.setSpacing(BINARY_WORKBENCH_LAYOUT.IMMEDIATE_SYMBOL_FIELD_SPACING)
        ok = symbol_button("OK", "preferences-ok", shell)
        cancel = symbol_button("Cancel", "preferences-cancel", shell)
        for button in (ok, cancel):
            button.setFixedSize(field_width, BINARY_WORKBENCH_LAYOUT.SYMBOL_INPUT_HEIGHT)
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        row.addLayout(_field_action_column(self.name_input, ok))
        row.addLayout(_field_action_column(value_input, cancel))
        shell_layout.addLayout(row)
        layout.addWidget(shell)


def _default_name(kind: str, value: str) -> str:
    prefix = "variable" if kind == BINARY_WORKBENCH_TEXT.VARIABLE_TARGET else "equate"
    cleaned = value.lower().replace("-", "minus_").replace("+", "").replace("0x", "")
    cleaned = SYMBOL_NAME_CLEANUP.sub("_", cleaned.replace("$", "")).strip("_")
    return f"{prefix}_{cleaned or 'value'}"


def _field_action_column(field, button) -> QVBoxLayout:
    layout = QVBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(BINARY_WORKBENCH_LAYOUT.IMMEDIATE_SYMBOL_ACTION_SPACING)
    layout.addWidget(field, 0, Qt.AlignLeft)
    layout.addWidget(button, 0, Qt.AlignLeft)
    return layout
