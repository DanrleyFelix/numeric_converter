from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor

from src.modules.dtos import BinaryWorkbenchEditRulesDTO, BinaryWorkbenchRowDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.cursor_guard import set_cursor_position
from src.presentation.ui.components.binary_workbench.editor.protected_edit import (
    remove_editor_block,
    replace_selection_preserving_line_breaks,
)
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import ROW_BYTES

COMMENT_LINE_PREFIX = "; "


class GridEditRulesMixin:
    def set_edit_rules(self, rules: BinaryWorkbenchEditRulesDTO) -> None:
        self._edit_rules = rules
        self.bytes.set_bytes_line_shift_allowed(rules.allow_byte_shift)

    def set_original_file_size(self, value: int) -> None:
        self._original_file_size = max(0, value)

    def _editor_change_allowed(self, editing_bytes: bool) -> bool:
        return self._edit_rules.allow_editor_edit

    def _rows_change_allowed(self, rows: list[BinaryWorkbenchRowDTO], editing_bytes: bool = False) -> bool:
        delta = len(rows) - len(self._rows)
        if self._edit_rules.allow_byte_shift or delta == 0:
            return True
        if self._free_offset_window():
            return True
        return self._virtual and not editing_bytes

    def _free_offset_window(self) -> bool:
        return (
            self._virtual
            and self._edit_rules.allow_free_edit_after_original_end
            and self._visible_start_offset >= self._original_boundary()
        )

    def _removed_only_extra_rows(self, rows: list[BinaryWorkbenchRowDTO]) -> bool:
        if not self._virtual:
            return False
        for index, current in enumerate(self._rows):
            offset = self._row_offset(index)
            if offset is not None and offset >= self._original_boundary():
                return True
            if index >= len(rows):
                return False
            if rows[index].offsets.get(BINARY_WORKBENCH_TEXT.FILE) != current.offsets.get(BINARY_WORKBENCH_TEXT.FILE):
                return False
            if rows[index].bytes_text != current.bytes_text:
                return False
        return False

    def _original_boundary(self) -> int:
        return self._original_file_size or self._total_size

    def _restore_editor_after_rejected_change(self, editing_bytes: bool) -> None:
        editor = self.bytes if editing_bytes else self.instructions
        values = [self._display_bytes_text(row.bytes_text) for row in self._rows] if editing_bytes else [self._display_instruction(row.instruction) for row in self._rows]
        self._set_editor_text(editor, values)
        self._render_raw_instructions()
        self._render_offsets()
        self._dirty_editor_kind = None
        self._remember_editor_text_signature(editor)
        self._emit_selection_summary()

    def _expanded_virtual_total_size(self, rows: list[BinaryWorkbenchRowDTO]) -> int:
        if not self._virtual:
            return self._total_size
        if not self._edit_rules.allow_byte_shift and not self._free_offset_window():
            return self._total_size
        if len(rows) <= len(self._rows):
            if self._free_offset_window() or self._removed_only_extra_rows(rows):
                return max(self._original_boundary(), self._visible_start_offset + (len(rows) * ROW_BYTES))
            return self._total_size
        return max(self._total_size, self._visible_start_offset + (len(rows) * ROW_BYTES))

    def _handle_editor_return_key(self, editor, event) -> None:
        if self._shift_return_should_insert_comment(editor, event):
            self._insert_comment_line(editor)
            editor.mark_return_key_handled()
            return
        if not self._return_key_should_navigate_virtual_offset(editor):
            return
        cursor = editor.textCursor()
        offset = self._row_offset(cursor.blockNumber())
        if offset is None:
            return
        self._move_to_instruction_offset(offset + ROW_BYTES)
        editor.mark_return_key_handled()

    def _handle_editor_protected_edit_key(self, editor, event) -> None:
        if self._protected_bytes_edit_key(editor):
            self._handle_protected_bytes_edit_key(editor, event)
            return
        if not self._protected_instruction_edit_key(editor):
            return
        cursor = editor.textCursor()
        if cursor.hasSelection():
            replace_selection_preserving_line_breaks(editor, cursor)
            editor.mark_protected_edit_key_handled()
            return
        row = cursor.blockNumber()
        if event.key() == Qt.Key_Backspace and cursor.positionInBlock() == 0:
            if self._remove_extra_instruction_row(editor, row):
                editor.mark_protected_edit_key_handled()
                return
            if self._remove_extra_instruction_row(editor, row - 1):
                editor.mark_protected_edit_key_handled()
                return
            if self._original_offset_row(row) or self._original_offset_row(row - 1):
                editor.mark_protected_edit_key_handled()
            return
        if event.key() == Qt.Key_Delete and cursor.positionInBlock() >= len(cursor.block().text()):
            if self._remove_extra_instruction_row(editor, row + 1):
                editor.mark_protected_edit_key_handled()
                return
            if self._original_offset_row(row) or self._original_offset_row(row + 1):
                editor.mark_protected_edit_key_handled()

    def _handle_protected_bytes_edit_key(self, editor, event) -> None:
        cursor = editor.textCursor()
        if cursor.hasSelection():
            replace_selection_preserving_line_breaks(editor, cursor)
            editor.mark_protected_edit_key_handled()
            return
        if event.key() == Qt.Key_Backspace and cursor.positionInBlock() == 0:
            editor.mark_protected_edit_key_handled()
            return
        if event.key() == Qt.Key_Delete and cursor.positionInBlock() >= len(cursor.block().text()):
            editor.mark_protected_edit_key_handled()

    def _protected_bytes_edit_key(self, editor) -> bool:
        return (
            self._virtual
            and editor is self.bytes
            and self._edit_rules.allow_editor_edit
            and not self._edit_rules.allow_byte_shift
            and not self._free_offset_window()
        )

    def _protected_instruction_edit_key(self, editor) -> bool:
        return (
            self._virtual
            and editor is self.instructions
            and self._edit_rules.allow_editor_edit
            and not self._edit_rules.allow_byte_shift
            and not self._free_offset_window()
        )

    def _remove_extra_instruction_row(self, editor, row: int) -> bool:
        if self._row_offset(row) is not None:
            return False
        return remove_editor_block(editor, row)

    def _original_offset_row(self, row: int) -> bool:
        offset = self._row_offset(row)
        return offset is not None and offset < self._original_boundary()

    def _return_key_should_navigate_virtual_offset(self, editor) -> bool:
        if not self._virtual or editor is not self.instructions:
            return False
        if not self._default_binary_append_rules_enabled():
            return False
        cursor = editor.textCursor()
        offset = self._row_offset(cursor.blockNumber())
        if cursor.hasSelection() or offset is None or offset >= self._original_boundary():
            return False
        return True

    def _shift_return_should_insert_comment(self, editor, event) -> bool:
        return (
            self._virtual
            and editor is self.instructions
            and self._edit_rules.allow_editor_edit
            and not self._edit_rules.allow_byte_shift
            and bool(event.modifiers() & Qt.ShiftModifier)
        )

    def _insert_comment_line(self, editor) -> None:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.EndOfBlock)
        cursor.insertText(f"\n{COMMENT_LINE_PREFIX}")
        editor.setTextCursor(cursor)

    def _default_binary_append_rules_enabled(self) -> bool:
        return (
            self._edit_rules.allow_free_edit_after_original_end
            and self._edit_rules.allow_editor_edit
            and not self._edit_rules.allow_byte_shift
        )

    def _move_to_instruction_offset(self, offset: int) -> None:
        row = self._row_for_offset(offset)
        if row is None and offset >= self._original_boundary():
            self._append_virtual_extra_offset()
            row = self._row_for_offset(offset)
        if row is None:
            self.set_visible_offset(offset)
            row = self._row_for_offset(offset)
        if row is not None:
            self._move_cursor_to_instruction_line(row)

    def _append_virtual_extra_offset(self) -> None:
        if not self._rows:
            return
        next_row = BinaryWorkbenchRowDTO(offsets=self._offsets_for_row(len(self._rows)), instruction="", bytes_text="")
        self._visible_start_offset += ROW_BYTES
        self._last_visible_offset = self._visible_start_offset
        self._total_size = max(
            self._total_size + ROW_BYTES,
            self._visible_start_offset + (len(self._rows) * ROW_BYTES),
        )
        self._rows = [*self._rows[1:], next_row]
        self._configure_scrollbar()
        self._render()

    def _move_cursor_to_instruction_line(self, index: int) -> None:
        block = self.instructions.document().findBlockByNumber(index)
        if not block.isValid():
            return
        cursor = self.instructions.textCursor()
        set_cursor_position(cursor, block.position() + len(block.text()))
        self.instructions.setTextCursor(cursor)
        self.instructions.setFocus()
