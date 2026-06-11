from src.modules.dtos import BinaryWorkbenchEditRulesDTO, BinaryWorkbenchRowDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.cursor_guard import (
    set_cursor_position,
)
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import ROW_BYTES


class GridEditRulesMixin:
    def set_edit_rules(self, rules: BinaryWorkbenchEditRulesDTO) -> None:
        self._edit_rules = rules

    def set_original_file_size(self, value: int) -> None:
        self._original_file_size = max(0, value)

    def _editor_change_allowed(self, editing_bytes: bool) -> bool:
        return self._edit_rules.allow_bytes_edit if editing_bytes else self._edit_rules.allow_assembly_edit

    def _rows_change_allowed(self, rows: list[BinaryWorkbenchRowDTO]) -> bool:
        delta = len(rows) - len(self._rows)
        if delta == 0:
            return True
        if self._extra_offset_window():
            return True
        if delta < 0 and self._removed_only_extra_rows(rows):
            return True
        if delta > 0:
            return self._insert_rows_allowed(rows)
        return self._edit_rules.allow_remove_shift

    def _insert_rows_allowed(self, rows: list[BinaryWorkbenchRowDTO]) -> bool:
        if self._edit_rules.allow_insert_shift:
            return True
        return self._edit_rules.allow_append_offsets and self._append_only_rows(rows)

    def _append_only_rows(self, rows: list[BinaryWorkbenchRowDTO]) -> bool:
        if len(rows) <= len(self._rows) or not self._edit_window_at_original_end():
            return False
        return all(
            self._preserves_existing_offset_bytes(candidate, current)
            for candidate, current in zip(rows, self._rows)
        )

    def _preserves_existing_offset_bytes(self, candidate: BinaryWorkbenchRowDTO, current: BinaryWorkbenchRowDTO) -> bool:
        return (
            candidate.offsets.get(BINARY_WORKBENCH_TEXT.FILE) == current.offsets.get(BINARY_WORKBENCH_TEXT.FILE)
            and candidate.bytes_text == current.bytes_text
        )

    def _edit_window_at_original_end(self) -> bool:
        if not self._virtual:
            return True
        return self._visible_start_offset + (len(self._rows) * ROW_BYTES) >= self._original_boundary()

    def _extra_offset_window(self) -> bool:
        return self._virtual and self._visible_start_offset >= self._original_boundary()

    def _removed_only_extra_rows(self, rows: list[BinaryWorkbenchRowDTO]) -> bool:
        if not self._virtual:
            return False
        for index, current in enumerate(self._rows):
            offset = self._row_offset(index)
            if offset is not None and offset >= self._original_boundary():
                return True
            if index >= len(rows) or not self._preserves_existing_offset_bytes(rows[index], current):
                return False
        return False

    def _original_boundary(self) -> int:
        return self._original_file_size or self._total_size

    def _restore_editor_after_rejected_change(self, editing_bytes: bool) -> None:
        editor = self.bytes if editing_bytes else self.instructions
        values = (
            [self._display_bytes_text(row.bytes_text) for row in self._rows]
            if editing_bytes
            else [self._display_instruction(row.instruction) for row in self._rows]
        )
        self._set_editor_text(editor, values)
        self._render_raw_instructions()
        self._render_offsets()
        self._dirty_editor_kind = None
        self._remember_editor_text_signature(editor)
        self._emit_selection_summary()

    def _expanded_virtual_total_size(self, rows: list[BinaryWorkbenchRowDTO]) -> int:
        if not self._virtual:
            return self._total_size
        if len(rows) <= len(self._rows):
            if self._extra_offset_window() or self._removed_only_extra_rows(rows):
                return max(self._original_boundary(), self._visible_start_offset + (len(rows) * ROW_BYTES))
            return self._total_size
        return max(self._total_size, self._visible_start_offset + (len(rows) * ROW_BYTES))

    def _handle_editor_return_key(self, editor) -> None:
        if not self._return_key_should_navigate_virtual_offset(editor):
            return
        cursor = editor.textCursor()
        offset = self._row_offset(cursor.blockNumber())
        if offset is None:
            return
        self._move_to_instruction_offset(offset + ROW_BYTES)
        editor.mark_return_key_handled()

    def _return_key_should_navigate_virtual_offset(self, editor) -> bool:
        if not self._virtual or editor is not self.instructions:
            return False
        if not self._default_binary_append_rules_enabled():
            return False
        cursor = editor.textCursor()
        offset = self._row_offset(cursor.blockNumber())
        if cursor.hasSelection() or offset is None or offset >= self._original_boundary():
            return False
        return cursor.positionInBlock() >= len(cursor.block().text())

    def _default_binary_append_rules_enabled(self) -> bool:
        return (
            self._edit_rules.allow_append_offsets
            and self._edit_rules.allow_assembly_edit
            and not self._edit_rules.allow_insert_shift
            and not self._edit_rules.allow_remove_shift
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
        next_row = BinaryWorkbenchRowDTO(
            offsets=self._offsets_for_row(len(self._rows)),
            instruction="",
            bytes_text="",
        )
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
