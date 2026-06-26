from PySide6.QtGui import QTextCursor

from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import BYTE_TOKEN


class GridSelectionRangesMixin:
    def _emit_bytes_selection(self, cursor: QTextCursor) -> None:
        selected = self._selected_byte_offsets(cursor)
        if not selected:
            self.selectionSummaryChanged.emit(self._cursor_summary(self.bytes, cursor))
            return
        first, last = min(selected), max(selected)
        self.selectionSummaryChanged.emit(
            f"Offset: 0x{self._byte_cursor_offset(cursor):08X} | "
            f"Selected: 0x{first:08X}..0x{last:08X} | Length: {len(selected)} bytes"
        )

    def _emit_instruction_selection(self, editor, cursor: QTextCursor) -> None:
        start_block = editor.document().findBlock(cursor.selectionStart()).blockNumber()
        end_position = max(cursor.selectionEnd() - 1, cursor.selectionStart())
        end_block = editor.document().findBlock(end_position).blockNumber()
        selected = [
            offset
            for index in range(start_block, end_block + 1)
            if (offset := self._row_offset(index)) is not None
        ]
        if not selected:
            self.selectionSummaryChanged.emit(self._cursor_summary(editor, cursor))
            return
        first, last = min(selected), max(selected) + ROW_BYTES - 1
        self.selectionSummaryChanged.emit(
            f"Offset: 0x{self._instruction_cursor_offset(cursor):08X} | "
            f"Selected: 0x{first:08X}..0x{last:08X} | Length: {len(selected) * ROW_BYTES} bytes"
        )

    def _cursor_summary(self, editor, cursor: QTextCursor) -> str:
        offset = (
            self._byte_cursor_offset(cursor)
            if editor is self.bytes
            else self._instruction_cursor_offset(cursor)
        )
        return f"Offset: 0x{offset:08X}"

    def _byte_cursor_offset(self, cursor: QTextCursor) -> int:
        block = cursor.block()
        byte_index = 0
        for index, match in enumerate(BYTE_TOKEN.finditer(block.text())):
            byte_index = index
            if cursor.positionInBlock() <= match.end():
                break
        return self._nearest_row_offset(block.blockNumber()) + byte_index

    def _instruction_cursor_offset(self, cursor: QTextCursor) -> int:
        return self._nearest_row_offset(cursor.blockNumber())

    def _selected_byte_offsets(self, cursor: QTextCursor) -> list[int]:
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        offsets: list[int] = []
        document = self.bytes.document()
        for block_number in range(document.blockCount()):
            block = document.findBlockByNumber(block_number)
            row_offset = self._row_offset(block_number)
            if not block.isValid() or row_offset is None:
                continue
            for byte_index, match in enumerate(BYTE_TOKEN.finditer(block.text())):
                token_start = block.position() + match.start()
                token_end = block.position() + match.end()
                if token_end > start and token_start < end:
                    offsets.append(row_offset + byte_index)
        return offsets

    def _byte_selection_positions(self, start_offset: int, end_offset: int) -> tuple[int, int] | None:
        start_row = self._row_for_offset(start_offset)
        end_row = self._row_for_offset(end_offset)
        if start_row is None or end_row is None:
            return None
        start_row_offset = self._row_offset(start_row)
        end_row_offset = self._row_offset(end_row)
        if start_row_offset is None or end_row_offset is None:
            return None
        start_byte = start_offset - start_row_offset
        end_byte = end_offset - end_row_offset
        document = self.bytes.document()
        start_block = document.findBlockByNumber(start_row)
        end_block = document.findBlockByNumber(end_row)
        if not start_block.isValid() or not end_block.isValid():
            return None
        start_tokens = list(BYTE_TOKEN.finditer(start_block.text()))
        end_tokens = list(BYTE_TOKEN.finditer(end_block.text()))
        if start_byte >= len(start_tokens) or end_byte >= len(end_tokens):
            return None
        start = start_block.position() + start_tokens[start_byte].start()
        end = end_block.position() + end_tokens[end_byte].end()
        return start, end

    def _row_offset(self, index: int) -> int | None:
        if not 0 <= index < len(self._rows):
            return None
        try:
            return int(self._rows[index].offsets.get("File", "-"), 16)
        except ValueError:
            return None

    def _nearest_row_offset(self, index: int) -> int:
        for candidate in [*range(index, len(self._rows)), *range(index - 1, -1, -1)]:
            if (offset := self._row_offset(candidate)) is not None:
                return offset
        return self._visible_start_offset

    def _row_for_offset(self, offset: int) -> int | None:
        return next(
            (
                index
                for index in range(len(self._rows))
                if (row_offset := self._row_offset(index)) is not None
                and row_offset <= offset < row_offset + ROW_BYTES
            ),
            None,
        )
