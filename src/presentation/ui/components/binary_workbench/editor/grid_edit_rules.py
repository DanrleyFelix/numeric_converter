from PySide6.QtCore import Qt
from PySide6.QtCore import QTimer
from PySide6.QtGui import QKeySequence, QTextCursor
from PySide6.QtWidgets import QApplication

from src.core.binary_workbench.byte_editing import (
    ByteEditViolation,
    ByteRowAccess,
    byte_edit_violation,
    byte_row_policy,
    removed_source_indices,
)
from src.core.binary_workbench.symbolic_instructions import preserved_source_annotation
from src.modules.binary_workbench_dtos import BinaryWorkbenchEditRulesDTO, BinaryWorkbenchRowDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.cursor_guard import set_cursor_position
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import (
    normalize_instruction_text,
)
from src.presentation.ui.components.binary_workbench.editor.protected_edit import (
    remove_editor_block,
    replace_selection_preserving_line_breaks,
)
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES

COMMENT_LINE_PREFIX = "; "


class GridEditRulesMixin:
    def set_edit_rules(self, rules: BinaryWorkbenchEditRulesDTO) -> None:
        self._edit_rules = rules
        self.bytes.set_bytes_line_shift_allowed(rules.allow_byte_shift)
        self.instructions.set_bytes_line_shift_allowed(rules.allow_byte_shift)

    def set_original_file_size(self, value: int) -> None:
        self._original_file_size = max(0, value)

    def _editor_change_allowed(self, editing_bytes: bool) -> bool:
        return self._edit_rules.allow_editor_edit

    def _rows_change_allowed(self, rows: list[BinaryWorkbenchRowDTO], editing_bytes: bool = False) -> bool:
        delta = len(rows) - len(self._rows)
        if editing_bytes and delta < 0 and self._removed_byte_rows_are_empty(rows):
            return True
        if self._edit_rules.allow_byte_shift or delta == 0:
            return True
        if self._free_offset_window():
            return True
        if not editing_bytes and self._valid_offset_count(rows) == self._valid_offset_count(self._rows):
            return True
        return self._virtual and not editing_bytes

    def _byte_lines_change_allowed(self, lines: list[str]) -> bool:
        if self._byte_transition_validated:
            return True
        previous = [self._display_bytes_row(row) for row in self._rows]
        violation = byte_edit_violation(
            previous,
            lines,
            self._byte_row_policies(),
            self._active_bytes_alignment_hint,
        )
        if violation is ByteEditViolation.NONE:
            return True
        self._emit_byte_edit_warning(violation)
        return False

    def _byte_row_policies(self):
        return tuple(
            byte_row_policy(row.instruction, bool(row.bytes_text))
            for row in self._rows
        )

    def _bytes_edit_event_allowed(self, editor, event) -> bool:
        if event.matches(QKeySequence.Undo) or event.matches(QKeySequence.Redo):
            return True
        policies = self._byte_row_policies()
        cursor = editor.textCursor()
        first, last = self._byte_edit_event_rows(cursor)
        removed_rows = self._byte_removed_rows(editor, event, first, last)
        if removed_rows:
            if not self._byte_rows_removable(removed_rows):
                self._emit_byte_edit_warning(ByteEditViolation.ROW_REMOVAL)
                return False
            if event.key() in {Qt.Key_Backspace, Qt.Key_Delete}:
                self._remove_bytes_rows(removed_rows, editor, event)
                return False
            editor.authorize_bytes_row_removal()
            return True
        touched = policies[first : last + 1]
        if any(item.access is ByteRowAccess.ASSEMBLY_ONLY for item in touched):
            self._emit_byte_edit_warning(ByteEditViolation.ASSEMBLY_ONLY)
            return False
        return True

    def _remove_bytes_rows(self, rows: tuple[int, ...], editor=None, event=None) -> None:
        """Remove validated plain or empty source rows from every projection."""

        first = min(rows)
        last = max(rows)
        if rows != tuple(range(first, last + 1)):
            return
        removed_rows = tuple(self._rows[first : last + 1])
        remaining_count = len(self._rows) - len(removed_rows)
        return_to_previous = bool(
            editor is not None
            and event is not None
            and event.key() == Qt.Key_Backspace
            and not editor.textCursor().hasSelection()
            and editor.textCursor().positionInBlock() == 0
        )
        target_row = first - 1 if return_to_previous else first
        target_row = min(max(0, target_row), max(0, remaining_count - 1))
        target_column = None if return_to_previous else 0
        shared_scroll = self.scrollbar.value()
        was_syncing = self._syncing_editor_change
        coordinator = getattr(self, "_consistency_coordinator", None)
        if coordinator is None or not coordinator.enabled():
            removed = set(rows)
            lines = [
                self._display_bytes_row(row)
                for index, row in enumerate(self._rows)
                if index not in removed
            ]
            self._replace_bytes_document_with_history(lines)
            self._sync_user_rows(lines, BINARY_WORKBENCH_TEXT.BYTES)
            return
        self._remember_removed_bytes_rows(first, removed_rows)
        self._syncing_editor_change = True
        try:
            self._remove_bytes_document_span(first, len(removed_rows))
        finally:
            self._syncing_editor_change = was_syncing
        coordinator.accept_bytes_structure_splice(first, len(removed_rows), [])
        self._remember_editor_text_signature(self.bytes)
        self._restore_bytes_removal_interaction(
            target_row,
            target_column,
            shared_scroll,
        )
        QTimer.singleShot(
            0,
            lambda: self._restore_bytes_removal_interaction(
                target_row,
                target_column,
                shared_scroll,
            ),
        )

    def _remove_bytes_document_span(self, first: int, removed: int) -> None:
        """Remove one contiguous Bytes span as a native undo command."""

        document = self.bytes.document()
        count = document.blockCount()
        cursor = QTextCursor(document)
        after = first + removed
        if after < count:
            start = document.findBlockByNumber(first).position()
            end = document.findBlockByNumber(after).position()
        else:
            end = document.characterCount() - 1
            start = document.findBlockByNumber(first).position()
            if first > 0:
                start -= 1
        cursor.beginEditBlock()
        try:
            set_cursor_position(cursor, start)
            set_cursor_position(cursor, end, QTextCursor.KeepAnchor)
            cursor.removeSelectedText()
        finally:
            cursor.endEditBlock()
    def _replace_bytes_document_with_history(self, lines: list[str]) -> None:
        """Replace a structural Bytes projection as one native undo command."""

        cursor = QTextCursor(self.bytes.document())
        cursor.beginEditBlock()
        try:
            cursor.select(QTextCursor.SelectionType.Document)
            cursor.insertText("\n".join(lines))
        finally:
            cursor.endEditBlock()

    def _restore_bytes_removal_interaction(
        self,
        target_row: int,
        target_column: int | None,
        shared_scroll: int,
    ) -> None:
        """Keep the Bytes caret on the row that replaced the removed row."""

        block = self.bytes.document().findBlockByNumber(target_row)
        column = len(block.text()) if target_column is None and block.isValid() else 0
        self.bytes._restore_cursor_viewport_state(target_row, column)
        target_scroll = min(shared_scroll, self.scrollbar.maximum())
        self._visible_start_offset = target_scroll
        self.scrollbar.setValue(target_scroll)
        if not self._virtual:
            self._scroll_static_document(target_scroll)

    def _byte_rows_removable(self, rows: tuple[int, ...]) -> bool:
        """Return whether every row is free of labels, comments and directives."""

        policies = self._byte_row_policies()
        return bool(rows) and all(
            0 <= row < len(policies) and policies[row].removable_from_bytes
            for row in rows
        )

    def _removed_byte_rows_are_empty(
        self,
        updated: list[BinaryWorkbenchRowDTO],
    ) -> bool:
        """Validate row-count reduction against stable source-row alignment."""

        previous = [self._display_bytes_row(row) for row in self._rows]
        current = [self._display_bytes_row(row) for row in updated]
        return self._byte_rows_removable(
            removed_source_indices(
                previous,
                current,
                self._active_bytes_alignment_hint,
            )
        )

    def _byte_edit_alignment_boundary(
        self,
        editor,
        event,
        first: int,
    ) -> int | None:
        """Return the exact source-row boundary targeted by one Bytes event."""

        # Undo/redo describes an already-recorded document splice.  The caret may
        # have moved anywhere since that splice was created, so using its current
        # row as an alignment hint maps restored Bytes onto unrelated Assembly
        # rows.  Let the stable prefix/suffix matcher recover the original span.
        if (
            event.matches(QKeySequence.Undo)
            or event.matches(QKeySequence.Redo)
            or (
                event.key() == Qt.Key_Z
                and bool(event.modifiers() & Qt.ControlModifier)
                and bool(event.modifiers() & Qt.ShiftModifier)
            )
        ):
            return None
        cursor = editor.textCursor()
        if cursor.hasSelection():
            selected = cursor.selection().toPlainText().replace("\u2029", "\n")
            return first if "\n" in selected else first + 1
        if event.key() in {Qt.Key_Return, Qt.Key_Enter}:
            if not cursor.block().text():
                return first + 1
            return first if cursor.positionInBlock() == 0 else first + 1
        if event.matches(QKeySequence.Paste) and "\n" in QApplication.clipboard().text():
            if not cursor.block().text():
                return first + 1
            return first if cursor.positionInBlock() == 0 else first + 1
        if event.key() == Qt.Key_Backspace and cursor.positionInBlock() == 0:
            return max(0, first - 1)
        if event.key() == Qt.Key_Delete and cursor.positionInBlock() >= len(cursor.block().text()):
            return first + 1
        return first

    def _byte_edit_event_rows(self, cursor: QTextCursor) -> tuple[int, int]:
        document = cursor.document()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        last_position = max(start, end - (1 if cursor.hasSelection() else 0))
        return (
            document.findBlock(start).blockNumber(),
            document.findBlock(last_position).blockNumber(),
        )

    def _byte_removed_rows(self, editor, event, first: int, last: int) -> tuple[int, ...]:
        cursor = editor.textCursor()
        selected_rows = self._fully_selected_byte_rows(editor, first, last)
        if event.key() in {Qt.Key_Backspace, Qt.Key_Delete} and selected_rows:
            return selected_rows
        if event.key() in {Qt.Key_Backspace, Qt.Key_Delete}:
            cleared = self._byte_rows_cleared_by_event(editor, event, first, last)
            if cleared:
                return cleared
        if cursor.hasSelection():
            replacement = ""
            if event.matches(QKeySequence.Paste):
                replacement = QApplication.clipboard().text().replace(
                    "\r\n", "\n"
                ).replace("\r", "\n")
            document_text = editor.toPlainText()
            start, end = cursor.selectionStart(), cursor.selectionEnd()
            updated = f"{document_text[:start]}{replacement}{document_text[end:]}"
            previous = [self._display_bytes_row(row) for row in self._rows]
            return removed_source_indices(
                previous,
                updated.split("\n"),
                self._bytes_edit_alignment_hint,
            )
        if event.key() == Qt.Key_Backspace and cursor.positionInBlock() == 0:
            if first <= 0:
                return ()
            if not cursor.block().text() or not self._byte_rows_removable((first,)):
                return (first,)
            return (first - 1,)
        if event.key() == Qt.Key_Delete and cursor.positionInBlock() >= len(cursor.block().text()):
            if not cursor.block().text() or not self._byte_rows_removable((first,)):
                return (first,)
            return (first + 1,)
        return ()

    def _fully_selected_byte_rows(
        self,
        editor,
        first: int,
        last: int,
    ) -> tuple[int, ...]:
        """Return an exact whole-row Bytes selection without content matching."""

        cursor = editor.textCursor()
        if not cursor.hasSelection():
            return ()
        first_block = editor.document().findBlockByNumber(first)
        last_block = editor.document().findBlockByNumber(last)
        if not first_block.isValid() or not last_block.isValid():
            return ()
        if cursor.selectionStart() != first_block.position():
            return ()
        if cursor.selectionEnd() != last_block.position() + len(last_block.text()):
            return ()
        return tuple(range(first, last + 1))

    def _byte_rows_cleared_by_event(
        self,
        editor,
        event,
        first: int,
        last: int,
    ) -> tuple[int, ...]:
        """Return complete byte-content rows cleared by Backspace or Delete."""

        cursor = editor.textCursor()
        text = editor.toPlainText()
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        if not cursor.hasSelection():
            position = cursor.position()
            if event.key() == Qt.Key_Backspace:
                start, end = max(0, position - 1), position
            else:
                start, end = position, min(len(text), position + 1)
        updated = f"{text[:start]}{text[end:]}"
        before = text.split("\n")
        after = updated.split("\n")
        if len(before) != len(after):
            return ()
        return tuple(
            row
            for row in range(first, last + 1)
            if 0 <= row < len(before)
            and bool("".join(before[row].split()))
            and not "".join(after[row].split())
        )

    def _emit_byte_edit_warning(self, violation: ByteEditViolation) -> None:
        message = (
            BINARY_WORKBENCH_TEXT.STATUS_BYTES_ROW_REMOVAL_BLOCKED
            if violation is ByteEditViolation.ROW_REMOVAL
            else BINARY_WORKBENCH_TEXT.STATUS_BYTES_ASSEMBLY_ONLY
        )
        self.commandWarningRequested.emit(message)

    def _valid_offset_count(self, rows: list[BinaryWorkbenchRowDTO]) -> int:
        return sum(1 for row in rows if row.offsets.get(BINARY_WORKBENCH_TEXT.FILE) not in {None, "-"})

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
        if editing_bytes:
            self._bytes_staged_incomplete = False
            self._bytes_staged_block = None
        current = editor.textCursor()
        position, anchor = current.position(), current.anchor()
        values = [self._display_bytes_row(row) for row in self._rows] if editing_bytes else [self._display_instruction(row.instruction) for row in self._rows]
        self._set_editor_text(editor, values)
        restored = QTextCursor(editor.document())
        set_cursor_position(restored, anchor)
        set_cursor_position(restored, position, QTextCursor.KeepAnchor)
        editor.setTextCursor(restored)
        self._render_raw_instructions()
        self._render_offsets()
        self._dirty_editor_kind = None
        self._remember_editor_text_signature(editor)
        self._emit_selection_summary()
        if editing_bytes:
            self._restore_bytes_column_alignment()

    def _restore_bytes_column_alignment(self) -> None:
        """Undo cursor-driven local scrolling after a rejected Bytes edit."""

        if not self._virtual:
            self._scroll_static_document(self.scrollbar.value())
            return
        self._reset_virtual_column_scrollbars()
        QTimer.singleShot(0, self._reset_virtual_column_scrollbars)

    def _reset_virtual_column_scrollbars(self) -> None:
        """Keep every virtual column anchored to its projected first row."""

        if not self._virtual:
            return
        for editor in (
            *self._offset_editors.values(),
            self.raw_instructions,
            self.bytes,
            self.decoded_text,
            self.instructions,
        ):
            editor.verticalScrollBar().setValue(0)

    def _expanded_virtual_total_size(
        self,
        rows: list[BinaryWorkbenchRowDTO],
        offset_delta: int = 0,
    ) -> int:
        if not self._virtual:
            return self._total_size
        if self._edit_rules.allow_byte_shift:
            return max(0, self._total_size + offset_delta)
        if not self._free_offset_window():
            return self._total_size
        if not offset_delta:
            return self._total_size
        return max(self._original_boundary(), self._total_size + offset_delta)

    def _handle_editor_return_key(self, editor, event) -> None:
        if editor is self.instructions:
            self.expand_collapsed_label_at_cursor(editor, True)
        if self._alt_return_event(event):
            if self._alt_return_should_insert_nop(editor):
                self._insert_nop_line(editor)
                editor.mark_return_key_handled()
            return
        if self._apply_instruction_command(editor):
            editor.mark_return_key_handled()
            return
        if self._shift_return_should_insert_comment(editor, event):
            self._insert_comment_line(editor)
            editor.mark_return_key_handled()
            return
        if self._return_key_should_insert_instruction_line(editor):
            self._insert_instruction_line(editor)
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
        if editor is self.bytes:
            cursor = editor.textCursor()
            first, last = self._byte_edit_event_rows(cursor)
            removed_rows = self._byte_removed_rows(editor, event, first, last)
            if removed_rows and self._byte_rows_removable(removed_rows):
                return
        if self._protected_annotated_bytes_edit_key(editor, event):
            self._handle_protected_bytes_edit_key(editor, event)
            return
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
            if self._instruction_line_deletion_locked():
                editor.mark_protected_edit_key_handled()
                return
            if self._original_offset_row(row) or self._original_offset_row(row - 1):
                editor.mark_protected_edit_key_handled()
            return
        if event.key() == Qt.Key_Delete and cursor.positionInBlock() >= len(cursor.block().text()):
            if self._remove_extra_instruction_row(editor, row + 1):
                editor.mark_protected_edit_key_handled()
                return
            if self._instruction_line_deletion_locked():
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

    def _protected_annotated_bytes_edit_key(self, editor, event) -> bool:
        if editor is not self.bytes or not self._edit_rules.allow_editor_edit:
            return False
        cursor = editor.textCursor()
        if cursor.hasSelection():
            document = editor.document()
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            first = document.findBlock(start).blockNumber() + 1
            last = document.findBlock(max(start, end - 1)).blockNumber()
            return any(
                start <= document.findBlockByNumber(row).position() - 1 < end
                and self._row_has_source_annotation(row)
                for row in range(first, last + 1)
            )
        row = cursor.blockNumber()
        if event.key() == Qt.Key_Backspace and cursor.positionInBlock() == 0:
            return self._row_has_source_annotation(row)
        if event.key() == Qt.Key_Delete and cursor.positionInBlock() >= len(cursor.block().text()):
            return self._row_has_source_annotation(row + 1)
        return False

    def _row_has_source_annotation(self, row: int) -> bool:
        return 0 <= row < len(self._rows) and bool(
            preserved_source_annotation(self._rows[row].instruction)
        )

    def _protected_instruction_edit_key(self, editor) -> bool:
        return (
            editor is self.instructions
            and self._edit_rules.allow_editor_edit
            and not self._edit_rules.allow_byte_shift
            and (
                not self._virtual
                or not self._free_offset_window()
            )
        )

    def _instruction_line_deletion_locked(self) -> bool:
        return not self._virtual and not self._edit_rules.allow_byte_shift

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
            editor is self.instructions
            and self._edit_rules.allow_editor_edit
            and bool(event.modifiers() & Qt.ShiftModifier)
        )

    def _alt_return_event(self, event) -> bool:
        return bool(event.modifiers() & Qt.AltModifier) and not bool(
            event.modifiers()
            & (Qt.ControlModifier | Qt.ShiftModifier | Qt.MetaModifier)
        )

    def _alt_return_should_insert_nop(self, editor) -> bool:
        return self._return_key_should_insert_instruction_line(editor)

    def _return_key_should_insert_instruction_line(self, editor) -> bool:
        return (
            not self._virtual
            and editor is self.instructions
            and self._edit_rules.allow_editor_edit
        )

    def _insert_instruction_line(self, editor) -> None:
        cursor = editor.textCursor()
        cursor.beginEditBlock()
        try:
            cursor.insertText("\n")
            self._normalize_previous_instruction_line(cursor)
        finally:
            cursor.endEditBlock()
        editor.setTextCursor(cursor)

    def _insert_nop_line(self, editor) -> None:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.EndOfBlock)
        cursor.beginEditBlock()
        try:
            cursor.insertText("\n")
            self._normalize_previous_instruction_line(cursor)
            cursor.insertText("nop\n")
        finally:
            cursor.endEditBlock()
        editor.setTextCursor(cursor)

    def _insert_comment_line(self, editor) -> None:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.EndOfBlock)
        cursor.beginEditBlock()
        try:
            cursor.insertText(f"\n{COMMENT_LINE_PREFIX}")
            self._normalize_previous_instruction_line(cursor)
        finally:
            cursor.endEditBlock()
        editor.setTextCursor(cursor)

    def _normalize_previous_instruction_line(self, cursor: QTextCursor) -> None:
        if not self._uppercase_instructions:
            return
        position = cursor.position()
        previous = cursor.block().previous()
        if not previous.isValid():
            return
        normalized = normalize_instruction_text(previous.text(), True)
        if normalized == previous.text():
            return
        set_cursor_position(cursor, previous.position())
        set_cursor_position(
            cursor,
            previous.position() + len(previous.text()),
            QTextCursor.KeepAnchor,
        )
        cursor.insertText(normalized)
        set_cursor_position(cursor, position)

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
