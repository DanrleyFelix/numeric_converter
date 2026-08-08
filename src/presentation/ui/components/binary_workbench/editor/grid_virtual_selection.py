from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication

from src.core.binary_workbench.clipboard_text import without_empty_lines
from src.core.binary_workbench.selection_limits import capped_end_offset
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.cursor_guard import (
    capture_logical_cursor,
    restore_logical_cursor,
    set_cursor_position,
)
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import BYTE_TOKEN


class GridVirtualSelectionMixin:
    def select_virtual_range(self, kind: str, start_offset: int, end_offset: int) -> None:
        if not self._virtual:
            return
        normalized_start, normalized_end = self._normalized_virtual_range(
            kind,
            start_offset,
            end_offset,
        )
        self._viewport_line_selection = None
        self._virtual_selection_anchor = normalized_start
        self._virtual_selection_kind = kind
        self._virtual_selection_range = (kind, normalized_start, normalized_end)
        self._select_visible_virtual_range(kind, normalized_start, normalized_end)
        editor = self._editor_for_selection_kind(kind)
        if editor is not None:
            editor.setFocus()
        self._emit_virtual_selection_summary(kind, normalized_start, normalized_end)

    def _copy_editor_selection(self, editor) -> None:
        """Copy the requested range without consuming its visual selection."""

        cursor_state = capture_logical_cursor(editor)
        self._selection_projection_timer.stop()
        self._selection_projection_request = None
        try:
            if self._virtual_selection_range is None:
                self._copy_local_editor_selection(editor)
                return
            kind, anchor_offset, cursor_offset = self._virtual_selection_range
            if kind != self._editor_kind_for_selection(editor):
                self._copy_local_editor_selection(editor)
                return
            first, last = sorted((anchor_offset, cursor_offset))
            self.copySelectionRequested.emit(
                kind,
                first,
                capped_end_offset(first, last, self._selection_limit_bytes),
            )
        finally:
            restore_logical_cursor(editor, cursor_state)

    def _copy_local_editor_selection(self, editor) -> None:
        kind = self._editor_kind_for_selection(editor)
        if kind not in {
            BINARY_WORKBENCH_TEXT.BYTES,
            BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS,
        }:
            editor.copy()
            return
        if not self._ensure_derived_copy(editor):
            return
        QApplication.clipboard().setText(
            without_empty_lines(editor.textCursor().selection().toPlainText())
        )

    def _ensure_derived_copy(self, editor) -> bool:
        """Verify copy-relevant derivations without blocking the GUI thread."""

        cursor = editor.textCursor()
        if not cursor.hasSelection():
            return True
        kind = self._editor_kind_for_selection(editor)
        coordinator = getattr(self, "_consistency_coordinator", None)
        if coordinator is None or kind is None:
            return True
        cursor_state = capture_logical_cursor(editor)
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        document = editor.document()
        first_block = document.findBlock(start)
        last_block = document.findBlock(max(start, end - 1))
        selection = (
            first_block.blockNumber(),
            last_block.blockNumber(),
            start - first_block.position(),
            end - last_block.position(),
            start == 0,
            end >= document.characterCount() - 1,
        )

        def copy_prepared(prepared_first, rows) -> None:
            """Keep the requested column bound to this asynchronous copy."""

            self._copy_prepared_derived_selection(
                editor,
                kind,
                prepared_first,
                rows,
                selection,
                cursor_state,
            )

        immediate = coordinator.request_broad_copy(
            first_block.blockNumber(),
            last_block.blockNumber(),
            copy_prepared,
        )
        restore_logical_cursor(editor, cursor_state)
        return immediate

    def _copy_prepared_derived_selection(
        self,
        editor,
        kind: str,
        prepared_first: int,
        rows,
        selection: tuple[int, int, int, int, bool, bool],
        cursor_state,
    ) -> None:
        """Copy only the selected column from immutable prepared rows."""

        first, last, start_column, end_column, starts_document, ends_document = selection
        local_first = first - prepared_first
        local_last = last - prepared_first
        if not 0 <= local_first <= local_last < len(rows):
            return
        display = (
            self._display_bytes_row
            if kind == BINARY_WORKBENCH_TEXT.BYTES
            else self._display_raw_row
        )
        lines = [display(rows[index]) for index in range(local_first, local_last + 1)]
        if len(lines) == 1:
            start_column = 0 if starts_document else start_column
            end_column = len(lines[0]) if ends_document else end_column
            lines[0] = lines[0][start_column:end_column]
        else:
            if not starts_document:
                lines[0] = lines[0][start_column:]
            if not ends_document:
                lines[-1] = lines[-1][:end_column]
        QApplication.clipboard().setText(without_empty_lines("\n".join(lines)))
        restore_logical_cursor(editor, cursor_state)

    def _capture_virtual_selection_anchor(self, editor) -> None:
        if not self._virtual:
            return
        kind = self._editor_kind_for_selection(editor)
        if kind is None:
            self._capture_viewport_line_selection(editor)
            self._virtual_selection_scrolling = True
            return
        if self._virtual_selection_anchor is not None and self._virtual_selection_kind == kind:
            self._virtual_selection_scrolling = True
            return
        self._capture_viewport_line_selection(editor)
        cursor = editor.textCursor()
        position = cursor.anchor() if cursor.hasSelection() else cursor.position()
        self._virtual_selection_anchor = self._offset_for_editor_position(editor, position)
        self._virtual_selection_kind = kind
        self._virtual_selection_scrolling = True

    def _restore_virtual_selection(self, editor) -> None:
        if not self._virtual or self._virtual_selection_anchor is None:
            return
        kind = self._editor_kind_for_selection(editor)
        if kind is None:
            if self._update_viewport_line_selection_cursor(
                editor,
                editor.textCursor().position(),
            ):
                self._restore_viewport_line_selection()
            self._virtual_selection_scrolling = False
            return
        if kind != self._virtual_selection_kind:
            self._virtual_selection_scrolling = False
            return
        cursor_offset = self._offset_for_editor_position(editor, editor.textCursor().position())
        self._virtual_selection_range = (kind, self._virtual_selection_anchor, cursor_offset)
        if self._update_viewport_line_selection_cursor(
            editor,
            editor.textCursor().position(),
        ):
            self._restore_viewport_line_selection()
        else:
            self._select_visible_virtual_range(
                kind,
                self._virtual_selection_anchor,
                cursor_offset,
            )
        self._emit_virtual_selection_summary(kind, self._virtual_selection_anchor, cursor_offset)
        self._virtual_selection_scrolling = False

    def _capture_virtual_viewport_selection(self, editor) -> None:
        if not self._virtual or not editor.textCursor().hasSelection():
            return
        kind = self._editor_kind_for_selection(editor)
        if self._virtual_selection_range is not None and self._virtual_selection_kind == kind:
            self._virtual_selection_scrolling = True
            return
        if (
            self._viewport_line_selection is None
            or self._viewport_editor_for_key(self._viewport_line_selection[0]) is not editor
        ):
            self._capture_viewport_line_selection(editor)
        if kind is None:
            return
        cursor = editor.textCursor()
        anchor_offset = self._offset_for_editor_position(editor, cursor.anchor())
        cursor_offset = self._offset_for_editor_position(editor, cursor.position())
        self._virtual_selection_anchor = anchor_offset
        self._virtual_selection_kind = kind
        self._virtual_selection_range = (kind, anchor_offset, cursor_offset)
        self._virtual_selection_scrolling = True

    def _finish_virtual_viewport_change(self, editor) -> None:
        if not self._virtual:
            self._virtual_selection_scrolling = False
            return
        if self._restore_viewport_line_selection():
            self._virtual_selection_scrolling = False
            return
        if self._virtual_selection_range is None:
            self._virtual_selection_scrolling = False
            return
        kind, anchor_offset, cursor_offset = self._virtual_selection_range
        if kind == self._editor_kind_for_selection(editor):
            self._select_visible_virtual_range(kind, anchor_offset, cursor_offset)
            self._emit_virtual_selection_summary(kind, anchor_offset, cursor_offset)
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
        self.bytes.verticalScrollBar().setValue(0)

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
        editor.verticalScrollBar().setValue(0)

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
        self._viewport_line_selection = None
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
