from PySide6.QtGui import QTextCursor

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import ROW_BYTES


class GridSelectionMixin:
    def select_offsets(self, start_offset: int, end_offset: int) -> None:
        if end_offset < self._visible_start_offset:
            return
        start = max(start_offset, self._visible_start_offset)
        end = min(end_offset, self._visible_start_offset + (len(self._rows) * ROW_BYTES) - 1)
        positions = self._byte_selection_positions(start, end)
        if positions is None:
            return
        cursor = self.bytes.textCursor()
        cursor.setPosition(positions[0])
        cursor.setPosition(positions[1], QTextCursor.KeepAnchor)
        self.bytes.setTextCursor(cursor)
        self.bytes.setFocus()
        self._emit_selection_summary()

    def select_instruction_offsets(self, start_offset: int, end_offset: int) -> None:
        if end_offset < self._visible_start_offset:
            return
        start_row = max(0, (start_offset - self._visible_start_offset) // ROW_BYTES)
        end_row = max(0, (end_offset - self._visible_start_offset) // ROW_BYTES)
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
        if self.instructions.hasFocus():
            return BINARY_WORKBENCH_TEXT.INSTRUCTION
        return self._last_editor_kind

    def _set_last_editor(self, kind: str) -> None:
        self._last_editor_kind = kind

    def set_default_editor_kind(self, kind: str) -> None:
        if self._last_editor_kind is None:
            self._last_editor_kind = kind

    def _select_all_focused_editor(self) -> None:
        editor = self.bytes if self.focused_editor_kind() == BINARY_WORKBENCH_TEXT.BYTES else self.instructions
        editor.selectAll()
        editor.setFocus()
        self._emit_selection_summary()

    def _emit_selection_summary(self) -> None:
        if self.bytes.textCursor().hasSelection():
            editor = self.bytes
        elif self.instructions.textCursor().hasSelection():
            editor = self.instructions
        else:
            editor = self.bytes if self.bytes.hasFocus() else self.instructions
        cursor = editor.textCursor()
        if not cursor.hasSelection():
            self.selectionSummaryChanged.emit(BINARY_WORKBENCH_TEXT.SELECTION_EMPTY)
            return
        self._emit_bytes_selection(cursor) if editor is self.bytes else self._emit_instruction_selection(cursor)
