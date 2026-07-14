from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QWidget

from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES
from src.presentation.ui.components.binary_workbench.editor.workbench_editor import (
    WorkbenchEditor,
)


class CenteredDashOverlay(QWidget):
    """Paint one centered offset placeholder without changing document text."""

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setPen(self.parentWidget().palette().text().color())
        width = self.parentWidget().fontMetrics().horizontalAdvance("-")
        left = max(0, (self.width() - width) // 2)
        painter.drawLine(left, self.height() // 2, left + width, self.height() // 2)


class OffsetWorkbenchEditor(WorkbenchEditor):
    """Render placeholder dashes at the visual center of an offset column."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._dash_labels: list[CenteredDashOverlay] = []

    def setPlainText(self, text: str) -> None:
        super().setPlainText(text)
        if hasattr(self, "_dash_labels"):
            self._rebuild_dash_labels()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_dash_labels()

    def scrollContentsBy(self, dx: int, dy: int) -> None:
        super().scrollContentsBy(dx, dy)
        self._position_dash_labels()

    def centered_dash_x(self) -> int:
        """Return the horizontal origin used to paint a centered dash."""

        width = self.fontMetrics().horizontalAdvance("-")
        return max(0, (self.viewport().width() - width) // 2)

    def _rebuild_dash_labels(self) -> None:
        """Hide native placeholder glyphs and create centered visual overlays."""

        for label in self._dash_labels:
            label.deleteLater()
        self._dash_labels.clear()
        block = self.document().firstBlock()
        transparent = QTextCharFormat()
        transparent.setForeground(QColor(0, 0, 0, 0))
        while block.isValid():
            if block.text().strip() == "-":
                cursor = QTextCursor(block)
                cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
                cursor.mergeCharFormat(transparent)
                label = CenteredDashOverlay(self.viewport())
                label.setAttribute(Qt.WA_TransparentForMouseEvents)
                label.setProperty("offsetBlock", block.blockNumber())
                label.show()
                self._dash_labels.append(label)
            block = block.next()
        self._position_dash_labels()

    def _position_dash_labels(self) -> None:
        """Keep every placeholder overlay aligned with its document line."""

        for label in getattr(self, "_dash_labels", []):
            block = self.document().findBlockByNumber(label.property("offsetBlock"))
            line_rect = self.cursorRect(QTextCursor(block))
            label.setGeometry(0, line_rect.top(), self.viewport().width(), line_rect.height())
            label.setVisible(block.isValid() and line_rect.bottom() >= 0)


class GridOffsetsMixin:
    def _row_at(self, index: int) -> BinaryWorkbenchRowDTO:
        if index < len(self._rows):
            return self._rows[index]
        return BinaryWorkbenchRowDTO(offsets=self._offsets_for_row(index))

    def _offsets_for_row(self, index: int) -> dict[str, str]:
        start_offset = self._visible_start_offset if self._virtual else 0
        file_offset = start_offset + (index * ROW_BYTES)
        bases = self._offset_bases()
        names = self._columns or [BINARY_WORKBENCH_TEXT.FILE]
        return {name: f"0x{bases.get(name, 0) + file_offset:08X}" for name in names}

    def _offset_bases(self) -> dict[str, int]:
        if not self._rows:
            return {BINARY_WORKBENCH_TEXT.FILE: 0}
        first = next(
            (
                row
                for row in self._rows
                if row.offsets.get(BINARY_WORKBENCH_TEXT.FILE, "-") != "-"
            ),
            None,
        )
        if first is None:
            return {BINARY_WORKBENCH_TEXT.FILE: 0}
        file_offset = offset_int(first.offsets.get(BINARY_WORKBENCH_TEXT.FILE) or first.offsets.get(BINARY_WORKBENCH_TEXT.FILE_OFFSET))
        return {
            name: offset_int(value) - file_offset
            for name, value in first.offsets.items()
        }

    def _aligned_scroll_offset(self, value: int) -> int:
        return max(0, value - (value % ROW_BYTES))


def offset_int(value: str | None) -> int:
    try:
        return int(value or "0x0", 16)
    except ValueError:
        return 0
