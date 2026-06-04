from PySide6.QtGui import QTextCursor

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT


class GridSelectionMixin:
    def select_offsets(self, start_offset: int, end_offset: int) -> None:
        positions = self._byte_selection_positions(start_offset, end_offset)
        if positions is None:
            return
        cursor = self.bytes.textCursor()
        cursor.setPosition(positions[0])
        cursor.setPosition(positions[1], QTextCursor.KeepAnchor)
        self.bytes.setTextCursor(cursor)
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
        cursor.setPosition(start_block.position())
        cursor.setPosition(end_block.position() + len(end_block.text()), QTextCursor.KeepAnchor)
        self.instructions.setTextCursor(cursor)
        self.instructions.setFocus()
        self._emit_selection_summary()

    def select_all_content(self) -> None:
        if self._virtual:
            self._select_all_focused_editor()
            return
        self._rows = list(self._all_rows)
        self._visible_start_offset = 0
        self._render()
        self._select_all_focused_editor()

    def assembly_text(self) -> str:
        return self.instructions.toPlainText()

    def focused_editor_kind(self) -> str | None:
        if self._last_editor_kind is not None:
            return self._last_editor_kind
        if self.bytes.hasFocus():
            return BINARY_WORKBENCH_TEXT.BYTES
        if self.raw_instructions.hasFocus():
            return BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS
        if self.instructions.hasFocus():
            return BINARY_WORKBENCH_TEXT.INSTRUCTION
        return self._last_editor_kind

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
        editor.selectAll()
        editor.setFocus()
        self._emit_selection_summary()

    def _emit_selection_summary(self) -> None:
        editor = self._selected_or_focused_editor()
        cursor = editor.textCursor()
        if not cursor.hasSelection():
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
