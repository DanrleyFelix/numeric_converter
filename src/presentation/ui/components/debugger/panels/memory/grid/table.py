from __future__ import annotations

from PySide6.QtCore import QRegularExpression, Signal, Qt
from PySide6.QtGui import (
    QAbstractTextDocumentLayout,
    QKeySequence,
    QRegularExpressionValidator,
    QTextDocument,
)
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemDelegate,
    QLineEdit,
    QStyle,
    QStyleOptionViewItem,
    QStyledItemDelegate,
    QTableWidget,
)

from src.presentation.ui.components.binary_workbench.editor.highlighters import (
    BytesHighlighter,
)


class HexBytesDelegate(QStyledItemDelegate):
    """Restrict memory editors to complete hexadecimal byte characters."""

    def createEditor(self, parent, option, index):
        """Create a hexadecimal and whitespace-only line editor."""

        editor = QLineEdit(parent)
        expression = QRegularExpression(r"[0-9A-Fa-f ]{0,11}")
        editor.setValidator(QRegularExpressionValidator(expression, editor))
        editor.textEdited.connect(lambda: self._advance_when_complete(editor))
        return editor

    def _advance_when_complete(self, editor: QLineEdit) -> None:
        """Commit four entered bytes and move to the next table cell."""

        if len("".join(editor.text().split())) != 8:
            return
        self.commitData.emit(editor)
        self.closeEditor.emit(
            editor,
            QAbstractItemDelegate.EndEditHint.EditNextItem,
        )

    def paint(self, painter, option, index) -> None:
        """Render byte cells through the existing Binary Workbench highlighter."""

        if index.column() == 0:
            super().paint(painter, option, index)
            return
        background = QStyleOptionViewItem(option)
        self.initStyleOption(background, index)
        background.text = ""
        style = background.widget.style() if background.widget else QApplication.style()
        style.drawControl(QStyle.CE_ItemViewItem, background, painter, background.widget)
        document = QTextDocument()
        document.setDefaultFont(option.font)
        document.setDocumentMargin(0)
        document.setPlainText(str(index.data() or ""))
        document.setTextWidth(max(1, option.rect.width() - 8))
        text_option = document.defaultTextOption()
        text_option.setAlignment(Qt.AlignCenter)
        document.setDefaultTextOption(text_option)
        highlighter = BytesHighlighter(document)
        highlighter.rehighlight()
        context = QAbstractTextDocumentLayout.PaintContext()
        painter.save()
        painter.translate(
            option.rect.left() + 4,
            option.rect.top()
            + (option.rect.height() - document.size().height()) / 2,
        )
        document.documentLayout().draw(painter, context)
        painter.restore()


class DebuggerMemoryTable(QTableWidget):
    """Reuse table selection while providing deterministic clipboard output."""

    pasteRequested = Signal(str, object)

    def keyPressEvent(self, event) -> None:
        """Copy selected memory cells or delegate all other key handling."""

        if event.matches(QKeySequence.Copy):
            rows: dict[int, list[tuple[int, str]]] = {}
            for item in (value for value in self.selectedItems() if value.column() > 0):
                rows.setdefault(item.row(), []).append((item.column(), item.text()))
            lines = [
                "\t".join(text for _column, text in sorted(values))
                for _row, values in sorted(rows.items())
            ]
            QApplication.clipboard().setText("\n".join(lines))
            event.accept()
            return
        if event.matches(QKeySequence.Paste):
            selected = tuple(
                sorted(
                    (item for item in self.selectedItems() if item.column() > 0),
                    key=lambda item: (item.row(), item.column()),
                )
            )
            self.pasteRequested.emit(QApplication.clipboard().text(), selected)
            event.accept()
            return
        super().keyPressEvent(event)
