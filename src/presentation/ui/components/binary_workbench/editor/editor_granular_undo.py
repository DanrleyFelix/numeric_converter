from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QTextCursor


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
        if event.modifiers() != Qt.NoModifier:
            return False
        if event.key() == Qt.Key_Backspace:
            operation = lambda cursor: cursor.deletePreviousChar()
        else:
            operation = lambda cursor: cursor.deleteChar()
        self._run_granular_edit(operation)
        return True

    def _handle_granular_insert(self, event: QKeyEvent) -> bool:
        if event.modifiers() & TEXT_INPUT_BLOCKED_MODIFIERS:
            return False
        text = event.text()
        if not text or text in {"\t", "\r", "\n"}:
            return False
        self._run_granular_edit(lambda cursor: cursor.insertText(text))
        return True

    def _run_granular_edit(self, operation: Callable[[QTextCursor], None]) -> None:
        if hasattr(self, "clear_editor_occurrence_selection"):
            self.clear_editor_occurrence_selection()
        cursor = self.textCursor()
        self._granular_editing = True
        cursor.beginEditBlock()
        try:
            operation(cursor)
        finally:
            cursor.endEditBlock()
            self._granular_editing = False
        self.setTextCursor(cursor)
