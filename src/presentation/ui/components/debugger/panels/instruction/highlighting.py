"""Debugger instruction-table rendering derived from established highlighters."""

from PySide6.QtCore import QRectF
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPalette,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
)
from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem

from src.presentation.ui.components.binary_workbench.editor.highlighters import (
    BytesHighlighter,
    InstructionHighlighter,
)

from src.presentation.ui.components.binary_workbench.editor.highlighter_colors import (
    psx_mips_highlight_color,
    psx_mips_required_highlight_color,
)
from src.presentation.ui.components.debugger.constants.layout import DEBUGGER_LAYOUT
from src.presentation.ui.helpers.load_qss import THEME_TOKENS


class SyntaxCellDelegate(QStyledItemDelegate):
    """Paint one table cell through a Binary Workbench syntax highlighter."""

    def __init__(self, highlighter_type, parent=None, **highlighter_options) -> None:
        """Bind the delegate to a QSyntaxHighlighter implementation."""

        super().__init__(parent)
        self._highlighter_type = highlighter_type
        self._highlighter_options = dict(highlighter_options)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        """Draw the item background and syntax-formatted text."""

        cell = QStyleOptionViewItem(option)
        self.initStyleOption(cell, index)
        text = cell.text
        cell.text = ""
        style = cell.widget.style() if cell.widget is not None else None
        if style is not None:
            style.drawControl(QStyle.CE_ItemViewItem, cell, painter, cell.widget)
        document = QTextDocument()
        document.setDocumentMargin(0)
        document.setDefaultFont(cell.font)
        document.setPlainText(text)
        text_option = document.defaultTextOption()
        text_option.setAlignment(cell.displayAlignment)
        document.setDefaultTextOption(text_option)
        default_format = QTextCharFormat()
        default_format.setForeground(cell.palette.color(QPalette.Text))
        cursor = QTextCursor(document)
        cursor.select(QTextCursor.Document)
        cursor.mergeCharFormat(default_format)
        highlighter = self._highlighter_type(
            document,
            **self._highlighter_options,
        )
        highlighter.rehighlight()
        content = cell.rect.adjusted(
            DEBUGGER_LAYOUT.SYNTAX_CELL_LEFT_PADDING,
            0,
            -DEBUGGER_LAYOUT.TABLE_CELL_PADDING,
            0,
        )
        document.setTextWidth(content.width())
        painter.save()
        painter.translate(content.left(), content.top() + (content.height() - document.size().height()) / 2)
        document.drawContents(painter, QRectF(0, 0, content.width(), content.height()))
        painter.restore()


def bytes_cell_delegate(parent=None) -> SyntaxCellDelegate:
    """Return a cell delegate using the exact Binary Workbench Bytes highlighter."""

    return SyntaxCellDelegate(BytesHighlighter, parent)


def instruction_cell_delegate(parent=None) -> SyntaxCellDelegate:
    """Return a cell delegate using the Binary Workbench instruction highlighter."""

    # Debugger rows already contain decoded branch immediates rather than the
    # Assembly source labels used by semantic navigation. Applying source-side
    # target validation here incorrectly paints valid relative immediates red.
    return SyntaxCellDelegate(
        InstructionHighlighter,
        parent,
        semantic_validation=False,
    )


def instruction_cell_color(column: int, value: str) -> str | None:
    """Return the shared Binary Workbench or state color for one cell."""

    if column == 1:
        return psx_mips_required_highlight_color("hex")
    if column == 5:
        if value == "ACTUAL":
            return psx_mips_highlight_color("registers", "$t0")
        if value == "LAST":
            return psx_mips_highlight_color("registers", "$sp")
        if value.startswith("EXEC"):
            return psx_mips_required_highlight_color("variable")
        if value.startswith("IGNORED"):
            return THEME_TOKENS["text-warning"]
        if value == "BREAK":
            return THEME_TOKENS["text-debug-write"]
        if value == "BREAKPOINT":
            return THEME_TOKENS["text-warning"]
        if value == "READY":
            return THEME_TOKENS["text-success"]
        if value == "ERROR":
            return THEME_TOKENS["text-danger"]
    return None
