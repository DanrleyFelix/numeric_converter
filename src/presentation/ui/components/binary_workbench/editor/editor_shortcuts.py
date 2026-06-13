from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QKeySequence, QTextCursor
from PySide6.QtWidgets import QApplication, QTextEdit

from src.presentation.ui.components.binary_workbench.editor.protected_edit import (
    replace_selection_preserving_line_breaks,
)

INSTRUCTIONS_PANEL = "binary-workbench-instructions-panel"


class EditorShortcutMixin:
    def setup_editor_shortcuts(self) -> None:
        self._large_binary_mode = False
        self._occurrence_query = ""
        self._occurrence_ranges: list[tuple[int, int]] = []

    def set_large_binary_mode(self, enabled: bool) -> None:
        self._large_binary_mode = enabled

    def handle_editor_shortcut(self, event: QKeyEvent) -> bool:
        key = event.key()
        modifiers = event.modifiers()
        if self._large_binary_mode and self._is_instruction_editor():
            if _alt_only(modifiers) and key in {Qt.Key_Up, Qt.Key_Down}:
                return True
            if _ctrl_shift_only(modifiers) and key in {Qt.Key_Up, Qt.Key_Down}:
                return True
            if self._handle_large_binary_line_break_replacement(event):
                return True
        if _ctrl_only(modifiers) and key == Qt.Key_D:
            return self._select_next_occurrence()
        if _ctrl_only(modifiers) and key == Qt.Key_Q:
            return self._select_only_next_occurrence()
        if _alt_only(modifiers) and key in {Qt.Key_Up, Qt.Key_Down}:
            return self._move_current_line(key == Qt.Key_Up)
        if _ctrl_shift_only(modifiers) and key in {Qt.Key_Up, Qt.Key_Down}:
            return self._duplicate_selected_lines(key == Qt.Key_Up)
        if len(self._occurrence_ranges) > 1:
            return self._handle_occurrence_edit(event)
        return self._block_large_binary_multiline_edit(event)

    def _handle_large_binary_line_break_replacement(self, event: QKeyEvent) -> bool:
        if not event.text() or event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier):
            return False
        cursor = self.textCursor()
        if not cursor.hasSelection() or "\n" not in cursor.selection().toPlainText():
            return False
        replace_selection_preserving_line_breaks(self, cursor, event.text())
        return True

    def clear_editor_occurrence_selection(self) -> None:
        if not self._occurrence_ranges and not self._occurrence_query:
            return
        self._occurrence_query = ""
        self._occurrence_ranges = []
        self.setExtraSelections([])

    def _select_next_occurrence(self) -> bool:
        query = self._selected_or_cursor_word()
        if not query:
            return False
        cursor = self.textCursor()
        current = (cursor.selectionStart(), cursor.selectionEnd())
        if query.casefold() != self._occurrence_query.casefold():
            self._occurrence_query = query
            self._occurrence_ranges = [current]
        elif current not in self._occurrence_ranges:
            self._occurrence_ranges.append(current)
        next_range = self._find_next_range(query, max(end for _, end in self._occurrence_ranges))
        if next_range is None:
            return False
        self._occurrence_ranges.append(next_range)
        self._apply_occurrence_selection(next_range)
        return True

    def _select_only_next_occurrence(self) -> bool:
        cursor = self.textCursor()
        query = self._selected_text() or self._occurrence_query
        if not query:
            query = self._selected_or_cursor_word()
        if not query:
            return False
        cursor = self.textCursor()
        current = (cursor.selectionStart(), cursor.selectionEnd())
        handled = current in self._occurrence_ranges
        remaining = [item for item in self._occurrence_ranges if item != current]
        excluded = {*remaining, current}
        next_range = self._find_next_range(query, cursor.selectionEnd(), excluded=excluded)
        self._occurrence_query = query
        if next_range is None:
            self._occurrence_ranges = remaining
            if remaining:
                self._apply_occurrence_selection(remaining[-1])
                return True
            cursor.clearSelection()
            self.setTextCursor(cursor)
            self.clear_editor_occurrence_selection()
            return handled
        self._occurrence_ranges = [*remaining, next_range]
        self._apply_occurrence_selection(next_range)
        return True

    def _move_current_line(self, up: bool) -> bool:
        if self.isReadOnly() or not self._is_instruction_editor():
            return False
        start, end = self._selected_block_range()
        if start != end:
            return False
        lines = self.toPlainText().split("\n")
        target = start - 1 if up else start + 1
        if target < 0 or target >= len(lines):
            return False
        lines[start], lines[target] = lines[target], lines[start]
        self._replace_lines(lines, target, target, True)
        return True

    def _duplicate_selected_lines(self, up: bool) -> bool:
        if self.isReadOnly() or self._large_binary_mode or not self._is_instruction_editor():
            return False
        start, end = self._selected_block_range()
        lines = self.toPlainText().split("\n")
        copied = lines[start : end + 1]
        insert_at = start if up else end + 1
        updated = [*lines[:insert_at], *copied, *lines[insert_at:]]
        self._replace_lines(updated, insert_at, insert_at + len(copied) - 1, False)
        return True

    def _handle_occurrence_edit(self, event: QKeyEvent) -> bool:
        if event.matches(QKeySequence.Copy):
            QApplication.clipboard().setText("\n".join(self._text_for_range(item) for item in self._occurrence_ranges))
            return True
        if event.matches(QKeySequence.Cut):
            QApplication.clipboard().setText("\n".join(self._text_for_range(item) for item in self._occurrence_ranges))
            self._replace_occurrence_ranges("")
            return True
        if event.matches(QKeySequence.Paste):
            self._replace_occurrence_ranges(QApplication.clipboard().text())
            return True
        if event.key() in {Qt.Key_Backspace, Qt.Key_Delete}:
            self._replace_occurrence_ranges("")
            return True
        if event.text() and not event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier):
            self._replace_occurrence_ranges(event.text())
            return True
        return False

    def _block_large_binary_multiline_edit(self, event: QKeyEvent) -> bool:
        if not self._large_binary_mode or not self._is_instruction_editor():
            return False
        if not self._selection_spans_multiple_blocks():
            return False
        if event.key() in {Qt.Key_Backspace, Qt.Key_Delete}:
            return False
        if event.matches(QKeySequence.Cut) or event.matches(QKeySequence.Paste):
            return True
        if event.matches(QKeySequence.Copy) or _ctrl_only(event.modifiers()):
            return False
        return bool(event.text())

    def _selected_or_cursor_word(self) -> str:
        text = self._selected_text()
        if text:
            return text
        cursor = self.textCursor()
        cursor.select(QTextCursor.WordUnderCursor)
        if not cursor.hasSelection():
            return ""
        self.setTextCursor(cursor)
        return self._selected_text()

    def _selected_text(self) -> str:
        return self.textCursor().selectedText().replace("\u2029", "\n")

    def _find_next_range(self, query: str, start: int, excluded: set[tuple[int, int]] | None = None) -> tuple[int, int] | None:
        text = self.toPlainText()
        needle = query.casefold()
        excluded = set(self._occurrence_ranges if excluded is None else excluded)
        for offset in (start, 0):
            index = text.casefold().find(needle, offset)
            while index >= 0:
                candidate = (index, index + len(query))
                if candidate not in excluded:
                    return candidate
                index = text.casefold().find(needle, index + 1)
        return None

    def _apply_occurrence_selection(self, active_range: tuple[int, int]) -> None:
        selections = []
        for start, end in self._occurrence_ranges:
            selection = QTextEdit.ExtraSelection()
            selection.cursor = QTextCursor(self.document())
            selection.cursor.setPosition(start)
            selection.cursor.setPosition(end, QTextCursor.KeepAnchor)
            selection.format.setBackground(self.palette().highlight())
            selection.format.setForeground(self.palette().highlightedText())
            selections.append(selection)
        self.setExtraSelections(selections)
        self._set_text_selection(*active_range)

    def _set_text_selection(self, start: int, end: int) -> None:
        cursor = QTextCursor(self.document())
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        self.setTextCursor(cursor)

    def _text_for_range(self, item: tuple[int, int]) -> str:
        start, end = item
        return self.toPlainText()[start:end]

    def _replace_occurrence_ranges(self, value: str) -> None:
        cursor = QTextCursor(self.document())
        cursor.beginEditBlock()
        for start, end in sorted(self._occurrence_ranges, reverse=True):
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.KeepAnchor)
            cursor.insertText(value)
        cursor.endEditBlock()
        self.clear_editor_occurrence_selection()

    def _selected_block_range(self) -> tuple[int, int]:
        cursor = self.textCursor()
        start = cursor.selectionStart()
        end = max(start, cursor.selectionEnd() - (1 if cursor.hasSelection() else 0))
        return self.document().findBlock(start).blockNumber(), self.document().findBlock(end).blockNumber()

    def _selection_spans_multiple_blocks(self) -> bool:
        cursor = self.textCursor()
        return cursor.hasSelection() and self._selected_block_range()[0] != self._selected_block_range()[1]

    def _replace_lines(self, lines: list[str], select_start: int, select_end: int, keep_selection: bool) -> None:
        cursor = QTextCursor(self.document())
        cursor.beginEditBlock()
        cursor.select(QTextCursor.Document)
        cursor.insertText("\n".join(lines))
        cursor.endEditBlock()
        start_block = self.document().findBlockByNumber(select_start)
        end_block = self.document().findBlockByNumber(select_end)
        if keep_selection:
            self._set_text_selection(start_block.position(), end_block.position() + len(end_block.text()))
            return
        cursor = self.textCursor()
        cursor.setPosition(end_block.position() + len(end_block.text()))
        self.setTextCursor(cursor)

    def _is_instruction_editor(self) -> bool:
        return self.objectName() == INSTRUCTIONS_PANEL


def _ctrl_only(modifiers: Qt.KeyboardModifiers) -> bool:
    return bool(modifiers & Qt.ControlModifier) and not bool(modifiers & (Qt.ShiftModifier | Qt.AltModifier | Qt.MetaModifier))


def _alt_only(modifiers: Qt.KeyboardModifiers) -> bool:
    return bool(modifiers & Qt.AltModifier) and not bool(modifiers & (Qt.ControlModifier | Qt.ShiftModifier | Qt.MetaModifier))


def _ctrl_shift_only(modifiers: Qt.KeyboardModifiers) -> bool:
    return bool(modifiers & Qt.ControlModifier) and bool(modifiers & Qt.ShiftModifier) and not bool(modifiers & (Qt.AltModifier | Qt.MetaModifier))
