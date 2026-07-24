"""Shared full-cell editor presentation for debugger tables."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit


def prepare_cell_editor(editor: QLineEdit) -> QLineEdit:
    """Style one line editor to occupy and visually match its complete cell."""

    editor.setObjectName("debugger-cell-editor")
    editor.setFrame(False)
    editor.setAlignment(Qt.AlignCenter)
    editor.setContentsMargins(0, 0, 0, 0)
    return editor


def fill_cell_editor(editor: QLineEdit, option) -> None:
    """Apply the exact delegate cell rectangle to an active editor."""

    editor.setGeometry(option.rect)
