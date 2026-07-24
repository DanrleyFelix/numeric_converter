"""Validated in-place editors for debugger register values."""

from typing import Literal

from PySide6.QtWidgets import QLineEdit, QStyledItemDelegate

from src.presentation.ui.components.binary_workbench.input_validators import (
    set_decimal_integer_validator,
    set_hex_offset_validator,
)
from src.presentation.ui.components.debugger.panels.table.editing import (
    fill_cell_editor,
    prepare_cell_editor,
)


class RegisterValueDelegate(QStyledItemDelegate):
    """Create a decimal-only or hexadecimal-only register editor."""

    def __init__(self, value_type: Literal["decimal", "hexadecimal"], parent=None) -> None:
        """Store the numeric representation accepted by this column."""

        super().__init__(parent)
        self._value_type = value_type

    def createEditor(self, parent, option, index) -> QLineEdit:
        """Return a line editor reusing the established numeric validators."""

        editor = prepare_cell_editor(QLineEdit(parent))
        if self._value_type == "decimal":
            set_decimal_integer_validator(editor)
        else:
            set_hex_offset_validator(editor)
        return editor

    def updateEditorGeometry(self, editor, option, _index) -> None:
        """Keep the register editor equal to its complete cell."""

        fill_cell_editor(editor, option)
