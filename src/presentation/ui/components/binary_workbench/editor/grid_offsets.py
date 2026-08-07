from PySide6.QtCore import Qt

from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES
from src.presentation.ui.components.binary_workbench.editor.workbench_editor import (
    WorkbenchEditor,
)


class CenteredDashWorkbenchEditor(WorkbenchEditor):
    """Paint visible placeholders without allocating one widget per source row."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._dash_blocks: set[int] = set()

    def centered_dash_x(self) -> int:
        """Return the horizontal origin used to paint a centered dash."""

        width = self.fontMetrics().horizontalAdvance("-")
        return max(0, (self.viewport().width() - width) // 2)

    def _rebuild_dash_labels(self) -> None:
        """Index placeholder rows without mutating the offset document."""

        self._dash_blocks.clear()
        block = self.document().firstBlock()
        while block.isValid():
            if block.text().strip() == "-":
                self._dash_blocks.add(block.blockNumber())
            block = block.next()
        self.viewport().update()

    def refresh_offset_block(self, index: int) -> None:
        """Refresh one changed offset without scanning the whole document."""

        self._dash_blocks.discard(index)
        block = self.document().findBlockByNumber(index)
        if block.isValid() and block.text().strip() == "-":
            self._dash_blocks.add(index)
        self.viewport().update()

    def splice_offset_blocks(self, first: int, removed: int, inserted: int) -> None:
        """Shift placeholder overlays after a structural document splice."""

        removed_end = first + removed
        delta = inserted - removed
        self._dash_blocks = {
            index if index < first else index + delta
            for index in self._dash_blocks
            if index < first or index >= removed_end
        }
        for index in range(first, first + inserted):
            block = self.document().findBlockByNumber(index)
            if block.isValid() and block.text().strip() == "-":
                self._dash_blocks.add(index)
        self.viewport().update()

    def refresh_dash_overlays(self) -> None:
        """Realign placeholder overlays after row visibility changes."""

        self.viewport().update()

class OffsetWorkbenchEditor(CenteredDashWorkbenchEditor):
    """Derived editor used by File and Reference Offset columns."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.set_content_alignment(Qt.AlignCenter)


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
        configured = {
            name: offset_int(value)
            for name, value in getattr(
                self,
                "_reference_offset_bases",
                {BINARY_WORKBENCH_TEXT.FILE: "0x00000000"},
            ).items()
        }
        configured.setdefault(BINARY_WORKBENCH_TEXT.FILE, 0)
        if not self._rows:
            return configured
        first = next(
            (
                row
                for row in self._rows
                if row.offsets.get(BINARY_WORKBENCH_TEXT.FILE, "-") != "-"
            ),
            None,
        )
        if first is None:
            return configured
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
