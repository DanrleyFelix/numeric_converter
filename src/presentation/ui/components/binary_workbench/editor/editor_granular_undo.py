from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QTextCursor

from src.presentation.ui.components.binary_workbench.editor.bytes_input import (
    bytes_delete_allowed,
    bytes_insert_allowed,
    is_bytes_editor,
)
from src.presentation.ui.components.binary_workbench.editor.cursor_guard import (
    set_cursor_position,
)
from src.presentation.ui.components.binary_workbench.editor.protected_edit import (
    replace_selection_preserving_line_breaks,
)


TEXT_INPUT_BLOCKED_MODIFIERS = (
    Qt.ControlModifier
    | Qt.AltModifier
    | Qt.MetaModifier
)


class EditorGranularUndoMixin:
    def handle_granular_text_edit(self, event: QKeyEvent) -> bool:
        if self.isReadOnly():
            return False
        if self._handle_granular_delete(event):
            return True
        if self._handle_granular_insert(event):
            return True
        return False

    def _handle_granular_delete(self, event: QKeyEvent) -> bool:
        if event.key() not in {Qt.Key_Backspace, Qt.Key_Delete}:
            return False
        if event.modifiers() & TEXT_INPUT_BLOCKED_MODIFIERS:
            return False
        if is_bytes_editor(self) and _bytes_delete_should_preserve_line_breaks(self):
            replace_selection_preserving_line_breaks(self, self.textCursor())
            return True
        if is_bytes_editor(self) and not bytes_delete_allowed(
            self,
            event.key() == Qt.Key_Backspace,
            self.bytes_line_shift_allowed() or self.bytes_row_removal_authorized(),
        ):
            return True
        if event.key() == Qt.Key_Backspace:
            operation = lambda cursor: cursor.deletePreviousChar()
        else:
            operation = lambda cursor: cursor.deleteChar()
        self._run_granular_edit(operation)
        return True

    def _handle_granular_insert(self, event: QKeyEvent) -> bool:
        if event.modifiers() & TEXT_INPUT_BLOCKED_MODIFIERS and not is_bytes_editor(self):
            return False
        text = event.text()
        if not text or text in {"\t", "\r", "\n"}:
            return False
        if is_bytes_editor(self) and not bytes_insert_allowed(
            text,
            self.toPlainText(),
            [(self.textCursor().selectionStart(), self.textCursor().selectionEnd())],
        ):
            return True
        def operation(cursor: QTextCursor) -> None:
            cursor.insertText(text)
            if is_bytes_editor(self) and hasattr(self, "normalize_granular_bytes_line"):
                self.normalize_granular_bytes_line(cursor)

        self._run_granular_edit(operation)
        return True

    def _run_granular_edit(self, operation: Callable[[QTextCursor], None]) -> None:
        """Run one edit block while preserving its resulting cursor range."""

        if hasattr(self, "clear_editor_occurrence_selection"):
            self.clear_editor_occurrence_selection()
        cursor = self.textCursor()
        self._granular_editing = True
        cursor.beginEditBlock()
        try:
            operation(cursor)
            position = cursor.position()
            anchor = cursor.anchor()
            if hasattr(self, "normalize_granular_instruction_line"):
                self.normalize_granular_instruction_line()
        finally:
            cursor.endEditBlock()
            self._granular_editing = False
        restored = QTextCursor(self.document())
        set_cursor_position(restored, anchor)
        set_cursor_position(restored, position, QTextCursor.KeepAnchor)
        self.setTextCursor(restored)


def _bytes_delete_should_preserve_line_breaks(editor) -> bool:
    cursor = editor.textCursor()
    selected = cursor.selection().toPlainText().replace("\u2029", "\n")
    return (
        cursor.hasSelection()
        and not editor.bytes_line_shift_allowed()
        and not editor.bytes_row_removal_authorized()
        and "\n" in selected
    )
