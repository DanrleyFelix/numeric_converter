from PySide6.QtGui import QTextCursor

from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import BYTE_TOKEN


class GridSelectionRangesMixin:
    def _emit_bytes_selection(self, cursor: QTextCursor) -> None:
        selected = self._selected_byte_range(cursor)
        if selected is None:
            self.selectionSummaryChanged.emit(self._cursor_summary(self.bytes, cursor))
            return
        first, last, count = selected
        self.selectionSummaryChanged.emit(
            f"Offset: 0x{self._byte_cursor_offset(cursor):08X} | "
            f"Selected: 0x{first:08X}..0x{last:08X} | Length: {count} bytes"
        )

    def _emit_instruction_selection(self, editor, cursor: QTextCursor) -> None:
        start_block = editor.document().findBlock(cursor.selectionStart()).blockNumber()
        end_position = max(cursor.selectionEnd() - 1, cursor.selectionStart())
        end_block = editor.document().findBlock(end_position).blockNumber()
        coordinator = getattr(self, "_consistency_coordinator", None)
        if coordinator is not None and coordinator.enabled():
            count = coordinator.emitted_bytes_between(start_block, end_block + 1)
            if not count:
                self.selectionSummaryChanged.emit(self._cursor_summary(editor, cursor))
                return
            first = coordinator.offset_before_line(start_block)
            self.selectionSummaryChanged.emit(
                f"Offset: 0x{self._instruction_cursor_offset(cursor):08X} | "
                f"Selected: 0x{first:08X}..0x{first + count - 1:08X} | "
                f"Length: {count} bytes"
            )
            return
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

    def _selected_byte_range(self, cursor: QTextCursor) -> tuple[int, int, int] | None:
        """Summarize Bytes with indexed middle rows and two token scans."""

        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        if start == end:
            return None
        document = self.bytes.document()
        first_block = document.findBlock(start)
        last_block = document.findBlock(max(start, end - 1))
        if not first_block.isValid() or not last_block.isValid():
            return None
        coordinator = getattr(self, "_consistency_coordinator", None)
        if coordinator is not None and coordinator.enabled():
            return self._indexed_byte_selection_range(
                first_block,
                last_block,
                start,
                end,
                coordinator,
            )
        return self._scanned_byte_selection_range(first_block, last_block, start, end)

    def _indexed_byte_selection_range(
        self,
        first_block,
        last_block,
        start: int,
        end: int,
        coordinator,
    ) -> tuple[int, int, int] | None:
        """Use contribution prefixes so drag cost does not grow with selection."""

        first_line = first_block.blockNumber()
        last_line = last_block.blockNumber()
        first_tokens = self._selected_token_indices(first_block, start, end)
        if first_line == last_line:
            if not first_tokens:
                return None
            base = coordinator.offset_before_line(first_line)
            return base + first_tokens[0], base + first_tokens[-1], len(first_tokens)
        last_tokens = self._selected_token_indices(last_block, start, end)
        middle_count = coordinator.emitted_bytes_between(first_line + 1, last_line)
        count = len(first_tokens) + middle_count + len(last_tokens)
        if not count:
            return None
        if first_tokens:
            first_offset = coordinator.offset_before_line(first_line) + first_tokens[0]
        else:
            first_offset = coordinator.offset_before_line(first_line + 1)
        if last_tokens:
            last_offset = coordinator.offset_before_line(last_line) + last_tokens[-1]
        else:
            last_offset = first_offset + count - 1
        return first_offset, last_offset, count

    @staticmethod
    def _selected_token_indices(block, start: int, end: int) -> list[int]:
        """Return at most four intersected byte indexes from one row."""

        return [
            index
            for index, match in enumerate(BYTE_TOKEN.finditer(block.text()))
            if block.position() + match.end() > start
            and block.position() + match.start() < end
        ]

    def _scanned_byte_selection_range(
        self,
        first_block,
        last_block,
        start: int,
        end: int,
    ) -> tuple[int, int, int] | None:
        """Retain a bounded fallback for virtual grids without an index."""

        first_offset: int | None = None
        last_offset: int | None = None
        count = 0
        block = first_block
        while block.isValid() and block.blockNumber() <= last_block.blockNumber():
            block_number = block.blockNumber()
            row_offset = self._row_offset(block_number)
            if row_offset is not None:
                for byte_index, match in enumerate(BYTE_TOKEN.finditer(block.text())):
                    token_start = block.position() + match.start()
                    token_end = block.position() + match.end()
                    if token_end <= start or token_start >= end:
                        continue
                    offset = row_offset + byte_index
                    first_offset = offset if first_offset is None else min(first_offset, offset)
                    last_offset = offset if last_offset is None else max(last_offset, offset)
                    count += 1
            block = block.next()
        if first_offset is None or last_offset is None:
            return None
        return first_offset, last_offset, count

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
        coordinator = getattr(self, "_consistency_coordinator", None)
        if coordinator is not None and coordinator.enabled():
            return coordinator.offset_before_line(index)
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
