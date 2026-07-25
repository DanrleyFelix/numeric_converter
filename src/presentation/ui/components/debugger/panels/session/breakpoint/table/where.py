"""Editable highlighted WHERE cells for debugger breakpoints."""

import re

from PySide6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import QLineEdit

from src.presentation.ui.components.binary_workbench.editor.highlighter_colors import (
    psx_mips_highlight_color,
    psx_mips_required_highlight_color,
)
from src.presentation.ui.components.binary_workbench.input_validators import (
    set_hex_offset_validator,
)
from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT
from src.presentation.ui.components.debugger.panels.instruction.highlighting import (
    SyntaxCellDelegate,
)
from src.presentation.ui.components.debugger.panels.table.editing import (
    fill_cell_editor,
    prepare_cell_editor,
)
from src.presentation.ui.helpers.load_qss import THEME_TOKENS

REGISTER = re.compile(r"\$[A-Za-z0-9_]+")
COMPARATOR = re.compile(r"<=|>=|!=|==|<|>")
LOGICAL = re.compile(r"\|\||&&|&|\b(?:or|and)\b", re.IGNORECASE)
HEX_VALUE = re.compile(r"(?<![\w$])-?0[xX][0-9A-Fa-f]+")
DECIMAL_VALUE = re.compile(r"(?<![\w$])-?\d+\b")


class BreakpointWhereHighlighter(QSyntaxHighlighter):
    """Color register conditions and hexadecimal address values."""

    def highlightBlock(self, text: str) -> None:
        """Apply the established register and immediate color families."""

        self._matches(
            HEX_VALUE,
            text,
            psx_mips_required_highlight_color("hex"),
        )
        self._matches(
            DECIMAL_VALUE,
            text,
            psx_mips_required_highlight_color("variable"),
        )
        operator_color = psx_mips_required_highlight_color("label")
        self._matches(COMPARATOR, text, operator_color)
        self._matches(
            LOGICAL,
            text,
            operator_color,
        )
        for match in REGISTER.finditer(text):
            color = psx_mips_highlight_color("registers", match.group())
            self._format(match.start(), len(match.group()), color)

    def _matches(self, pattern, text: str, color: str) -> None:
        """Color every match of one breakpoint syntax category."""

        for match in pattern.finditer(text):
            self._format(match.start(), len(match.group()), color)

    def _format(self, start: int, length: int, color: str | None) -> None:
        """Apply a foreground color when the category resolved one."""

        if color is None:
            return
        style = QTextCharFormat()
        style.setForeground(QColor(color))
        self.setFormat(start, length, style)


class BreakpointWhereDelegate(SyntaxCellDelegate):
    """Paint WHERE syntax and constrain address-mode edits to hexadecimal."""

    def __init__(self, parent=None) -> None:
        super().__init__(BreakpointWhereHighlighter, parent)

    def createEditor(self, parent, option, index):
        """Create a condition editor or a strict hexadecimal address editor."""

        editor = prepare_cell_editor(QLineEdit(parent))
        type_value = str(
            index.siblingAtColumn(
                DEBUGGER_LAYOUT.BREAKPOINT_TYPE_COLUMN
            ).data()
            or ""
        )
        if type_value != "reg":
            set_hex_offset_validator(editor)
        return editor

    def updateEditorGeometry(self, editor, option, _index) -> None:
        """Keep the WHERE editor equal to its complete cell."""

        fill_cell_editor(editor, option)
