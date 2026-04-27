from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QKeySequence, QTextCursor
from PySide6.QtWidgets import QApplication, QPlainTextEdit

from src.presentation.ui.components.converter_panel.helpers import (
    display_position_from_raw_index,
    is_valid_char,
    normalize_char,
    raw_index_from_display_position,
    within_limit,
)


class ConverterInputEdit(QPlainTextEdit):
    valueEdited = Signal(str, str)

    def __init__(self, input_type: str):
        super().__init__()
        self.input_type = input_type
        self._raw_value = ""
        self._desired_raw_cursor_index: int | None = None
        self.setMinimumHeight(40)
        self.setTabChangesFocus(True)

    @property
    def raw_value(self) -> str:
        return self._raw_value

    def set_content(self, raw_value: str, display_value: str) -> None:
        restore_raw_index = self._desired_raw_cursor_index
        if restore_raw_index is None and self.hasFocus():
            restore_raw_index = raw_index_from_display_position(
                self.toPlainText(),
                self._raw_value,
                self.textCursor().position(),
            )
        self._raw_value = raw_value
        self.setPlainText(display_value)
        if restore_raw_index is None:
            self._move_cursor_to_end()
        else:
            self._set_cursor_from_raw_index(restore_raw_index)
        self._desired_raw_cursor_index = None

    def copy_raw_to_clipboard(self) -> None:
        QApplication.clipboard().setText("".join(self.toPlainText().split()))

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.matches(QKeySequence.Copy) or event.matches(QKeySequence.SelectAll):
            super().keyPressEvent(event)
            return
        if event.matches(QKeySequence.Cut):
            self.copy()
            self._delete_selection()
            event.accept()
            return
        if event.matches(QKeySequence.Paste):
            self._replace_selection_or_insert(QApplication.clipboard().text())
            event.accept()
            return
        if event.key() == Qt.Key_Backspace:
            self._backspace()
            event.accept()
            return
        if event.key() == Qt.Key_Delete:
            self._delete()
            event.accept()
            return
        if event.key() in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down, Qt.Key_Home, Qt.Key_End):
            super().keyPressEvent(event)
            return
        text = event.text()
        if text and event.modifiers() in (Qt.KeyboardModifier.NoModifier, Qt.KeyboardModifier.KeypadModifier):
            self._replace_selection_or_insert(text)
            event.accept()
            return
        event.accept()

    def _replace_selection_or_insert(self, text: str) -> None:
        insert_text = "".join(
            normalize_char(self.input_type, char)
            for char in text
            if is_valid_char(self.input_type, char)
        )
        if not insert_text:
            return
        start, end = self._selected_raw_range()
        candidate = self._raw_value[:start] + insert_text + self._raw_value[end:]
        if not within_limit(self.input_type, candidate):
            return
        self._raw_value = candidate
        self._desired_raw_cursor_index = start + len(insert_text)
        self.valueEdited.emit(self.input_type, self._raw_value)

    def _backspace(self) -> None:
        start, end = self._selected_raw_range()
        if start != end:
            self._delete_raw_range(start, end)
            return
        if start > 0:
            self._delete_raw_range(start - 1, start)

    def _delete(self) -> None:
        start, end = self._selected_raw_range()
        if start != end:
            self._delete_raw_range(start, end)
            return
        if start < len(self._raw_value):
            self._delete_raw_range(start, start + 1)

    def _delete_selection(self) -> None:
        start, end = self._selected_raw_range()
        if start != end:
            self._delete_raw_range(start, end)

    def _delete_raw_range(self, start: int, end: int) -> None:
        self._raw_value = self._raw_value[:start] + self._raw_value[end:]
        self._desired_raw_cursor_index = start
        self.valueEdited.emit(self.input_type, self._raw_value)

    def _selected_raw_range(self) -> tuple[int, int]:
        cursor = self.textCursor()
        if not cursor.hasSelection():
            index = raw_index_from_display_position(
                self.toPlainText(),
                self._raw_value,
                cursor.position(),
            )
            return index, index
        start = raw_index_from_display_position(self.toPlainText(), self._raw_value, cursor.selectionStart())
        end = raw_index_from_display_position(self.toPlainText(), self._raw_value, cursor.selectionEnd())
        return min(start, end), max(start, end)

    def _set_cursor_from_raw_index(self, raw_index: int) -> None:
        display_position = display_position_from_raw_index(
            self.toPlainText(),
            self._raw_value,
            raw_index,
        )
        cursor = self.textCursor()
        cursor.setPosition(display_position)
        self.setTextCursor(cursor)

    def _move_cursor_to_end(self) -> None:
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)
