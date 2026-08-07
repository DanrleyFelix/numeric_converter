from PySide6.QtGui import QTextCursor

from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.cursor_guard import (
    set_cursor_position,
)


class GridSelectionMixin:
    def _queue_selection_projection(self, editor) -> None:
        """Debounce a complete-line selection as one bounded read demand."""

        if self._updating:
            return
        selected = self._fully_selected_line_range(editor)
        if selected is None:
            self._selection_projection_timer.stop()
            self._selection_projection_request = None
            return
        kind = self._projection_kind_for_editor(editor)
        if kind is None:
            self._selection_projection_timer.stop()
            self._selection_projection_request = None
            return
        first, last = selected
        if last - first + 1 > 256:
            # Broad copy already owns the consistency barrier.  Selection
            # feedback must never synchronously derive an entire document.
            self._selection_projection_timer.stop()
            self._selection_projection_request = None
            return
        self._selection_projection_request = (kind, first, last)
        self._selection_projection_timer.start()

    def _fully_selected_line_range(self, editor) -> tuple[int, int] | None:
        """Return only rows whose complete textual contents are selected."""

        cursor = editor.textCursor()
        if not cursor.hasSelection():
            return None
        document = editor.document()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        first = document.findBlock(start)
        if first.isValid() and start > first.position():
            first = first.next()
        last = document.findBlock(max(start, end - 1))
        if last.isValid() and end < last.position() + len(last.text()):
            last = last.previous()
        if not first.isValid() or not last.isValid():
            return None
        if first.blockNumber() > last.blockNumber():
            return None
        return first.blockNumber(), last.blockNumber()

    def _projection_kind_for_editor(self, editor) -> str | None:
        """Map a selected column without consulting the current focus state."""

        if editor is self.bytes:
            return BINARY_WORKBENCH_TEXT.BYTES
        if editor is self.raw_instructions:
            return BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS
        if editor is self.decoded_text:
            return BINARY_WORKBENCH_TEXT.DECODED_TEXT
        if editor is self.instructions:
            return BINARY_WORKBENCH_TEXT.INSTRUCTION
        return None

    def _materialize_selected_projection(self) -> None:
        """Materialize only the fully selected column rows on explicit demand."""

        requested = self._selection_projection_request
        self._selection_projection_request = None
        if requested is None:
            return
        kind, first, last = requested
        coordinator = getattr(self, "_consistency_coordinator", None)
        if coordinator is not None:
            coordinator.materialize_selected_projection(kind, first, last)

    def select_offsets(self, start_offset: int, end_offset: int) -> None:
        positions = self._byte_selection_positions(start_offset, end_offset)
        if positions is None:
            return
        cursor = self.bytes.textCursor()
        set_cursor_position(cursor, positions[0])
        set_cursor_position(cursor, positions[1], QTextCursor.KeepAnchor)
        self.bytes.setTextCursor(cursor)
        self._set_last_editor(BINARY_WORKBENCH_TEXT.BYTES)
        self.bytes.setFocus()
        self._emit_selection_summary()

    def select_instruction_offsets(self, start_offset: int, end_offset: int) -> None:
        start_row = self._row_for_offset(start_offset)
        end_row = self._row_for_offset(end_offset)
        if start_row is None or end_row is None:
            return
        document = self.instructions.document()
        start_block = document.findBlockByNumber(start_row)
        end_block = document.findBlockByNumber(end_row)
        if not start_block.isValid() or not end_block.isValid():
            return
        cursor = self.instructions.textCursor()
        set_cursor_position(cursor, start_block.position())
        set_cursor_position(cursor, end_block.position() + len(end_block.text()), QTextCursor.KeepAnchor)
        self.instructions.setTextCursor(cursor)
        self._set_last_editor(BINARY_WORKBENCH_TEXT.INSTRUCTION)
        self.instructions.setFocus()
        self._emit_selection_summary()

    def point_instruction_offset(self, offset: int) -> None:
        row = self._row_for_offset(offset)
        if row is None:
            return
        block = self.instructions.document().findBlockByNumber(row)
        if not block.isValid():
            return
        cursor = self.instructions.textCursor()
        set_cursor_position(cursor, block.position())
        self.instructions.setTextCursor(cursor)
        self._set_last_editor(BINARY_WORKBENCH_TEXT.INSTRUCTION)
        self.instructions.setFocus()
        self._emit_selection_summary()

    def select_all_content(self) -> None:
        if self._virtual:
            if self._total_size <= 0:
                return
            kind = self.focused_editor_kind() or BINARY_WORKBENCH_TEXT.INSTRUCTION
            self.set_visible_offset(0)
            self.select_virtual_range(kind, 0, min(self._total_size, self._selection_limit_bytes) - 1)
            return
        self._select_all_focused_editor()

    def assembly_text(self) -> str:
        return "\n".join(row.instruction for row in self.export_rows())

    def focused_editor_kind(self) -> str | None:
        if self.bytes.hasFocus():
            return BINARY_WORKBENCH_TEXT.BYTES
        if self.raw_instructions.hasFocus():
            return BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS
        if self.instructions.hasFocus():
            return BINARY_WORKBENCH_TEXT.INSTRUCTION
        return self._last_editor_kind

    def current_cursor_offset(self) -> int:
        editor = self._editor_for_selection_kind(
            self.focused_editor_kind() or BINARY_WORKBENCH_TEXT.INSTRUCTION
        )
        if editor is self.bytes:
            return self._byte_cursor_offset(editor.textCursor())
        return self._instruction_cursor_offset(editor.textCursor())

    def _set_last_editor(self, kind: str) -> None:
        self._last_editor_kind = kind

    def set_default_editor_kind(self, kind: str) -> None:
        if self._last_editor_kind is None:
            self._last_editor_kind = kind

    def _select_all_focused_editor(self) -> None:
        editors = {
            BINARY_WORKBENCH_TEXT.BYTES: self.bytes,
            BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS: self.raw_instructions,
            BINARY_WORKBENCH_TEXT.INSTRUCTION: self.instructions,
        }
        editor = editors.get(self.focused_editor_kind(), self.instructions)
        self._select_editor_to_limit(editor)
        editor.setFocus()
        self._emit_selection_summary()

    def _select_editor_to_limit(self, editor) -> None:
        valid_rows = 0
        last_row = -1
        for index in range(len(self._rows)):
            if self._row_offset(index) is not None:
                valid_rows += 1
            last_row = index
            if valid_rows * ROW_BYTES >= self._selection_limit_bytes:
                break
        if last_row < 0 or last_row >= editor.document().blockCount() - 1:
            editor.selectAll()
            return
        end_block = editor.document().findBlockByNumber(last_row)
        cursor = editor.textCursor()
        set_cursor_position(cursor, 0)
        set_cursor_position(
            cursor,
            end_block.position() + len(end_block.text()),
            QTextCursor.KeepAnchor,
        )
        editor.setTextCursor(cursor)

    def _emit_selection_summary(self) -> None:
        editor = self._selected_or_focused_editor()
        cursor = editor.textCursor()
        if not cursor.hasSelection():
            if self._viewport_line_selection is not None and (
                self._updating or self._virtual_selection_scrolling
            ):
                return
            if self._virtual_selection_range is not None:
                kind, anchor_offset, cursor_offset = self._virtual_selection_range
                self._emit_virtual_selection_summary(kind, anchor_offset, cursor_offset)
                return
            if self._virtual_selection_scrolling:
                return
            self._clear_virtual_selection()
            self.selectionSummaryChanged.emit(self._cursor_summary(editor, cursor))
            return
        if self._virtual_selection_range is not None:
            kind, anchor_offset, cursor_offset = self._virtual_selection_range
            self._emit_virtual_selection_summary(kind, anchor_offset, cursor_offset)
            return
        self._emit_bytes_selection(cursor) if editor is self.bytes else self._emit_instruction_selection(editor, cursor)

    def _selected_or_focused_editor(self):
        for editor in (self.bytes, self.raw_instructions, self.instructions):
            if editor.textCursor().hasSelection():
                return editor
        for editor in (self.bytes, self.raw_instructions, self.instructions):
            if editor.hasFocus():
                return editor
        return self.instructions
