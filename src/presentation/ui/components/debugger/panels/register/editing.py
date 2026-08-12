"""Validated in-place editors for debugger register values."""

from typing import Literal

from PySide6.QtGui import QValidator
from PySide6.QtWidgets import QLineEdit, QStyledItemDelegate
from src.presentation.ui.components.debugger.panels.table.editing import (
    fill_cell_editor,
    prepare_cell_editor,
)


class RegisterValueDelegate(QStyledItemDelegate):
    """Create a decimal-only or hexadecimal-only register editor."""

    def __init__(
        self,
        value_type: Literal["decimal", "hexadecimal"],
        parent=None,
        bits: int = 32,
    ) -> None:
        """Store the numeric representation accepted by this column."""

        super().__init__(parent)
        self._value_type = value_type
        self._bits = bits

    def createEditor(self, parent, option, index) -> QLineEdit:
        """Return a line editor reusing the established numeric validators."""

        editor = prepare_cell_editor(QLineEdit(parent))
        base = 10 if self._value_type == "decimal" else 16
        editor.setValidator(UnsignedRegisterValidator(base, self._bits, editor))
        return editor

    def updateEditorGeometry(self, editor, option, _index) -> None:
        """Keep the register editor equal to its complete cell."""

        fill_cell_editor(editor, option)


class UnsignedRegisterValidator(QValidator):
    """Accept one unsigned register value without silently truncating it."""

    def __init__(self, base: int, bits: int, parent=None) -> None:
        """Configure the accepted numeric base and native register width."""

        super().__init__(parent)
        self._base = base
        self._maximum = (1 << bits) - 1

    def validate(self, value: str, position: int):
        """Return a Qt validation state for one partially typed value."""

        text = value.strip()
        if not text or self._base == 16 and text.casefold() == "0x":
            return QValidator.Intermediate, value, position
        digits = text[2:] if self._base == 16 and text.casefold().startswith("0x") else text
        allowed = "0123456789" if self._base == 10 else "0123456789abcdefABCDEF"
        if not digits or any(character not in allowed for character in digits):
            return QValidator.Invalid, value, position
        try:
            parsed = int(digits, self._base)
        except ValueError:
            return QValidator.Invalid, value, position
        state = QValidator.Acceptable if parsed <= self._maximum else QValidator.Invalid
        return state, value, position
