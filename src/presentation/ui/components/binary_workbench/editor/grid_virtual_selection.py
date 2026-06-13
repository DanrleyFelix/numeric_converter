from PySide6.QtGui import QTextCursor

from src.core.binary_workbench.selection_limits import capped_end_offset
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.cursor_guard import (
    set_cursor_position,
)
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import BYTE_TOKEN, ROW_BYTES


class GridVirtualSelectionMixin:
    def select_virtual_range(self, kind: str, start_offset: int, end_offset: int) -> None:
        if not self._virtual:
            return
        normalized_start, normalized_end = self._normalized_virtual_range(
            kind,
            start_offset,
            end_offset,
        )
        self._virtual_selection_anchor = normalized_start
        self._virtual_selection_kind = kind
        self._virtual_selection_range = (kind, normalized_start, normalized_end)
        self._select_visible_virtual_range(kind, normalized_start, normalized_end)
        editor = self._editor_for_selection_kind(kind)
        if editor is not None:
            editor.setFocus()
        self._emit_virtual_selection_summary(kind, normalized_start, normalized_end)

    def _copy_editor_selection(self, editor) -> None:
        if self._virtual_selection_range is None:
            editor.copy()
            return
        kind, anchor_offset, cursor_offset = self._virtual_selection_range
        if kind != self._editor_kind_for_selection(editor):
            editor.copy()
            return
        first, last = sorted((anchor_offset, cursor_offset))
        self.copySelectionRequested.emit(
            kind,
            first,
            capped_end_offset(first, last, self._selection_limit_bytes),
        )

    def _capture_virtual_selection_anchor(self, editor) -> None:
        if not self._virtual:
            return
        kind = self._editor_kind_for_selection(editor)
        if kind is None:
            return
        if self._virtual_selection_anchor is not None and self._virtual_selection_kind == kind:
            self._virtual_selection_scrolling = True
            return
        cursor = editor.textCursor()
        position = cursor.anchor() if cursor.hasSelection() else cursor.position()
        self._virtual_selection_anchor = self._offset_for_editor_position(editor, position)
        self._virtual_selection_kind = kind
        self._virtual_selection_scrolling = True

    def _restore_virtual_selection(self, editor) -> None:
        if not self._virtual or self._virtual_selection_anchor is None:
            return
        kind = self._editor_kind_for_selection(editor)
        if kind is None or kind != self._virtual_selection_kind:
            self._virtual_selection_scrolling = False
            return
        cursor_offset = self._offset_for_editor_position(editor, editor.textCursor().position())
        self._virtual_selection_range = (kind, self._virtual_selection_anchor, cursor_offset)
        self._select_visible_virtual_range(kind, self._virtual_selection_anchor, cursor_offset)
        self._emit_virtual_selection_summary(kind, self._virtual_selection_anchor, cursor_offset)
        self._virtual_selection_scrolling = False

    def _select_visible_virtual_range(self, kind: str, anchor_offset: int, cursor_offset: int) -> None:
        visible = [self._row_offset(index) for index in range(len(self._rows))]
        visible = [offset for offset in visible if offset is not None]
        if not visible:
            return
        first_visible = min(visible)
        last_visible = max(visible) + ROW_BYTES - 1
        first, last = sorted((anchor_offset, cursor_offset))
        start = max(first, first_visible)
        end = min(last, last_visible)
        if start > end:
            return
        if kind == BINARY_WORKBENCH_TEXT.BYTES:
            self._select_visible_byte_range(start, end)
            return
        self._select_visible_instruction_range(kind, start, end)

    def _select_visible_byte_range(self, start_offset: int, end_offset: int) -> None:
        positions = self._byte_selection_positions(start_offset, end_offset)
        if positions is None:
            return
        cursor = self.bytes.textCursor()
        set_cursor_position(cursor, positions[0])
        set_cursor_position(cursor, positions[1], QTextCursor.KeepAnchor)
        self.bytes.setTextCursor(cursor)

    def _select_visible_instruction_range(self, kind: str, start_offset: int, end_offset: int) -> None:
        start_row = self._row_for_offset(start_offset)
        end_row = self._row_for_offset(end_offset)
        if start_row is None or end_row is None:
            return
        editor = self.raw_instructions if kind == BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS else self.instructions
        document = editor.document()
        start_block = document.findBlockByNumber(start_row)
        end_block = document.findBlockByNumber(end_row)
        if not start_block.isValid() or not end_block.isValid():
            return
        cursor = editor.textCursor()
        set_cursor_position(cursor, start_block.position())
        set_cursor_position(cursor, end_block.position() + len(end_block.text()), QTextCursor.KeepAnchor)
        editor.setTextCursor(cursor)

    def _emit_virtual_selection_summary(self, kind: str, anchor_offset: int, cursor_offset: int) -> None:
        first, last = sorted((anchor_offset, cursor_offset))
        if kind == BINARY_WORKBENCH_TEXT.BYTES:
            length = last - first + 1
            end = last
        else:
            length = (((last - first) // ROW_BYTES) + 1) * ROW_BYTES
            end = last + ROW_BYTES - 1
        self.selectionSummaryChanged.emit(
            f"Offset: 0x{cursor_offset:08X} | "
            f"Selected: 0x{first:08X}..0x{end:08X} | Length: {length} bytes"
        )

    def _clear_virtual_selection(self, *_args) -> None:
        self._virtual_selection_anchor = None
        self._virtual_selection_kind = None
        self._virtual_selection_range = None
        self._virtual_selection_scrolling = False

    def _editor_kind_for_selection(self, editor) -> str | None:
        if editor is self.bytes:
            return BINARY_WORKBENCH_TEXT.BYTES
        if editor is self.raw_instructions:
            return BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS
        if editor is self.instructions:
            return BINARY_WORKBENCH_TEXT.INSTRUCTION
        return None

    def _editor_for_selection_kind(self, kind: str):
        if kind == BINARY_WORKBENCH_TEXT.BYTES:
            return self.bytes
        if kind == BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS:
            return self.raw_instructions
        if kind == BINARY_WORKBENCH_TEXT.INSTRUCTION:
            return self.instructions
        return None

    def _normalized_virtual_range(
        self,
        kind: str,
        start_offset: int,
        end_offset: int,
    ) -> tuple[int, int]:
        first, last = sorted((max(0, start_offset), max(0, end_offset)))
        if kind == BINARY_WORKBENCH_TEXT.BYTES:
            return first, last
        word_size = max(1, self._codec.word_size)
        return first - (first % word_size), last - (last % word_size)

    def _offset_for_editor_position(self, editor, position: int) -> int:
        document = editor.document()
        block = document.findBlock(position)
        if not block.isValid():
            return self._visible_start_offset
        if editor is self.bytes:
            return self._byte_offset_for_block_position(block.blockNumber(), position - block.position())
        return self._nearest_row_offset(block.blockNumber())

    def _byte_offset_for_block_position(self, block_number: int, position_in_block: int) -> int:
        block = self.bytes.document().findBlockByNumber(block_number)
        row_offset = self._row_offset(block_number)
        if not block.isValid() or row_offset is None:
            return self._visible_start_offset
        byte_index = 0
        for index, match in enumerate(BYTE_TOKEN.finditer(block.text())):
            byte_index = index
            if position_in_block <= match.end():
                break
        return row_offset + byte_index
