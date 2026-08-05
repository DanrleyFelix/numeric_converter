from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPalette, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QWidget

from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES
from src.presentation.ui.components.binary_workbench.editor.workbench_editor import (
    WorkbenchEditor,
)


class CenteredDashOverlay(QWidget):
    """Paint one centered gray placeholder without changing document text."""

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setPen(self.parentWidget().palette().color(QPalette.PlaceholderText))
        painter.setFont(self.parentWidget().font())
        painter.drawText(
            self.rect(),
            Qt.AlignCenter,
            str(self.property("placeholderText") or "-"),
        )


class CenteredDashWorkbenchEditor(WorkbenchEditor):
    """Render placeholder dashes at the visual center of a derived column."""

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
        """Restore offset text visibility and rebuild centered dash overlays."""

        for label in self._dash_labels:
            label.deleteLater()
        self._dash_labels.clear()
        block = self.document().firstBlock()
        while block.isValid():
            self._format_offset_block(block)
            block = block.next()
        self._position_dash_labels()

    def refresh_offset_block(self, index: int) -> None:
        """Refresh one changed offset without scanning the whole document."""

        retained = []
        for label in self._dash_labels:
            if label.property("offsetBlock") == index:
                label.deleteLater()
            else:
                retained.append(label)
        self._dash_labels = retained
        block = self.document().findBlockByNumber(index)
        if block.isValid():
            self._format_offset_block(block)
        self._position_dash_labels()

    def splice_offset_blocks(self, first: int, removed: int, inserted: int) -> None:
        """Shift placeholder overlays after a structural document splice."""

        after = first + removed
        delta = inserted - removed
        retained = []
        for label in self._dash_labels:
            index = int(label.property("offsetBlock"))
            if first <= index < after:
                label.deleteLater()
                continue
            if index >= after:
                label.setProperty("offsetBlock", index + delta)
            retained.append(label)
        self._dash_labels = retained
        for index in range(first, first + inserted):
            block = self.document().findBlockByNumber(index)
            if block.isValid():
                self._format_offset_block(block)
        self._position_dash_labels()

    def refresh_dash_overlays(self) -> None:
        """Realign placeholder overlays after row visibility changes."""

        self._position_dash_labels()

    def _format_offset_block(self, block) -> None:
        """Make an address visible or replace a dash with its overlay."""

        cursor = QTextCursor(block)
        cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        placeholder = block.text().strip()
        is_placeholder = placeholder == "-"
        if block.text():
            text_format = QTextCharFormat()
            if is_placeholder:
                text_format.setForeground(QColor(0, 0, 0, 0))
            cursor.setCharFormat(text_format)
        if not is_placeholder:
            return
        label = CenteredDashOverlay(self.viewport())
        label.setAttribute(Qt.WA_TransparentForMouseEvents)
        label.setProperty("offsetBlock", block.blockNumber())
        label.setProperty("placeholderText", placeholder)
        label.show()
        self._dash_labels.append(label)

    def _position_dash_labels(self) -> None:
        """Keep every placeholder overlay aligned with its document line."""

        for label in getattr(self, "_dash_labels", []):
            block = self.document().findBlockByNumber(label.property("offsetBlock"))
            line_rect = self.cursorRect(QTextCursor(block))
            label.setGeometry(0, line_rect.top(), self.viewport().width(), line_rect.height())
            label.setVisible(
                block.isValid()
                and block.isVisible()
                and line_rect.bottom() >= 0
            )


class OffsetWorkbenchEditor(CenteredDashWorkbenchEditor):
    """Derived editor used by File and Reference Offset columns."""


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
