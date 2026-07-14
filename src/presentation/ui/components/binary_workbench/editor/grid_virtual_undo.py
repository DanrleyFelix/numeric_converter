from PySide6.QtCore import QSignalBlocker
from PySide6.QtGui import QTextCursor

from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_TEXT,
)


class GridVirtualUndoMixin:
    """Serialize undo-bearing viewport documents while they are not visible."""

    def _reset_virtual_undo_cache(self) -> None:
        self._virtual_undo_cache: dict[str, dict[int, tuple[list[str], str, list[str]]]] = {
            BINARY_WORKBENCH_TEXT.BYTES: {},
            BINARY_WORKBENCH_TEXT.INSTRUCTION: {},
        }

    def _capture_virtual_undo(self, previous_offset: int, target_offset: int) -> None:
        if previous_offset == target_offset:
            return
        for kind, editor in self._virtual_undo_editors():
            state = self._serialized_undo_state(editor)
            if state is None:
                self._virtual_undo_cache[kind].pop(previous_offset, None)
            else:
                self._virtual_undo_cache[kind][previous_offset] = state

    def _restore_virtual_undo(self, offset: int) -> None:
        for kind, editor in self._virtual_undo_editors():
            state = self._virtual_undo_cache[kind].get(offset)
            if state is not None and editor.toPlainText() == state[1]:
                self._rebuild_undo_state(editor, state)

    def _serialized_undo_state(self, editor):
        document = editor.document()
        if not document.isUndoAvailable() and not document.isRedoAvailable():
            return None
        blocker = QSignalBlocker(editor)
        undo_states: list[str] = []
        while document.isUndoAvailable():
            document.undo()
            undo_states.append(editor.toPlainText())
        for _ in undo_states:
            document.redo()
        current = editor.toPlainText()
        redo_states: list[str] = []
        while document.isRedoAvailable():
            document.redo()
            redo_states.append(editor.toPlainText())
        for _ in redo_states:
            document.undo()
        del blocker
        return list(reversed(undo_states)), current, redo_states

    def _rebuild_undo_state(self, editor, state) -> None:
        undo_states, current, redo_states = state
        blocker = QSignalBlocker(editor)
        was_updating = self._updating
        self._updating = True
        try:
            states = [*undo_states, current]
            editor.setPlainText(states[0])
            for text in states[1:]:
                self._replace_document_text(editor, text)
            for text in redo_states:
                self._replace_document_text(editor, text)
            for _ in redo_states:
                editor.document().undo()
            self._remember_editor_text_signature(editor)
        finally:
            self._updating = was_updating
            del blocker

    def _replace_document_text(self, editor, text: str) -> None:
        cursor = QTextCursor(editor.document())
        cursor.beginEditBlock()
        cursor.select(QTextCursor.Document)
        cursor.insertText(text)
        cursor.endEditBlock()

    def _virtual_undo_editors(self):
        return (
            (BINARY_WORKBENCH_TEXT.BYTES, self.bytes),
            (BINARY_WORKBENCH_TEXT.INSTRUCTION, self.instructions),
        )
