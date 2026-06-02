from PySide6.QtGui import QTextCursor

from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import BYTE_TOKEN, ROW_BYTES


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

    def _emit_instruction_selection(self, cursor: QTextCursor) -> None:
        editor = self.instructions
        start_block = editor.document().findBlock(cursor.selectionStart()).blockNumber()
        end_position = max(cursor.selectionEnd() - 1, cursor.selectionStart())
        end_block = editor.document().findBlock(end_position).blockNumber()
        first = self._visible_start_offset + (start_block * ROW_BYTES)
        last = self._visible_start_offset + ((end_block + 1) * ROW_BYTES) - 1
        self.selectionSummaryChanged.emit(
            f"Offset: 0x{self._instruction_cursor_offset(cursor):08X} | "
            f"Selected: 0x{first:08X}..0x{last:08X} | Length: {last - first + 1} bytes"
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
        return self._visible_start_offset + (block.blockNumber() * ROW_BYTES) + byte_index

    def _instruction_cursor_offset(self, cursor: QTextCursor) -> int:
        return self._visible_start_offset + (cursor.blockNumber() * ROW_BYTES)

    def _selected_byte_offsets(self, cursor: QTextCursor) -> list[int]:
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        offsets: list[int] = []
        document = self.bytes.document()
        for block_number in range(document.blockCount()):
            block = document.findBlockByNumber(block_number)
            if not block.isValid():
                continue
            for byte_index, match in enumerate(BYTE_TOKEN.finditer(block.text())):
                token_start = block.position() + match.start()
                token_end = block.position() + match.end()
                if token_end > start and token_start < end:
                    offsets.append(self._visible_start_offset + (block_number * ROW_BYTES) + byte_index)
        return offsets

    def _byte_selection_positions(self, start_offset: int, end_offset: int) -> tuple[int, int] | None:
        start_row = (start_offset - self._visible_start_offset) // ROW_BYTES
        end_row = (end_offset - self._visible_start_offset) // ROW_BYTES
        start_byte = (start_offset - self._visible_start_offset) % ROW_BYTES
        end_byte = (end_offset - self._visible_start_offset) % ROW_BYTES
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
