from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout

from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.environment.symbols_dialog_widgets import (
    symbol_button,
    symbol_input,
    size_symbol_action,
)


class AddCommandDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("preferences-dialog")
        self.setWindowTitle(BINARY_WORKBENCH_TEXT.ADD_COMMAND)
        self.setFixedSize(
            BINARY_WORKBENCH_LAYOUT.ADD_COMMAND_DIALOG_WIDTH,
            BINARY_WORKBENCH_LAYOUT.ADD_COMMAND_DIALOG_HEIGHT,
        )
        layout = QVBoxLayout(self)
        margin = BINARY_WORKBENCH_LAYOUT.ADD_COMMAND_DIALOG_MARGIN
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(BINARY_WORKBENCH_LAYOUT.ADD_COMMAND_DIALOG_GAP)
        self.name_input = symbol_input(
            BINARY_WORKBENCH_TEXT.COMMAND_NAME,
            self,
            "",
            BINARY_WORKBENCH_LAYOUT.ADD_COMMAND_FIELD_WIDTH,
        )
        self.name_input.returnPressed.connect(self.accept)
        ok = symbol_button(BINARY_WORKBENCH_TEXT.OK, "preferences-ok", self)
        size_symbol_action(ok, BINARY_WORKBENCH_LAYOUT.ADD_COMMAND_FIELD_WIDTH)
        ok.clicked.connect(self.accept)
        layout.addWidget(self.name_input)
        layout.addWidget(ok, 0, Qt.AlignCenter)

    def command_name(self) -> str:
        return self.name_input.text().strip()


def ask_command_name(parent=None) -> str:
    dialog = AddCommandDialog(parent)
    if dialog.exec() != dialog.DialogCode.Accepted:
        return ""
    return dialog.command_name()
