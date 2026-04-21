from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QTextCursor, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QToolButton,
    QVBoxLayout,
)

from src.core.converter.errors import MAX_BYTE_LENGTH
from src.presentation.ui.design.icons import Icons


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
            restore_raw_index = self._raw_index_from_display_position(
                self.textCursor().position()
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
        if text and event.modifiers() in (
            Qt.KeyboardModifier.NoModifier,
            Qt.KeyboardModifier.KeypadModifier,
        ):
            self._replace_selection_or_insert(text)
            event.accept()
            return

        event.accept()

    def _replace_selection_or_insert(self, text: str) -> None:
        insert_text = "".join(
            self._normalize_char(char)
            for char in text
            if self._is_valid_char(char)
        )
        if not insert_text:
            return

        start, end = self._selected_raw_range()
        candidate = self._raw_value[:start] + insert_text + self._raw_value[end:]
        if not self._within_limit(candidate):
            return

        self._raw_value = candidate
        self._desired_raw_cursor_index = start + len(insert_text)
        self.valueEdited.emit(self.input_type, self._raw_value)

    def _backspace(self) -> None:
        start, end = self._selected_raw_range()
        if start != end:
            self._delete_raw_range(start, end)
            return

        if start <= 0:
            return
        self._delete_raw_range(start - 1, start)

    def _delete(self) -> None:
        start, end = self._selected_raw_range()
        if start != end:
            self._delete_raw_range(start, end)
            return

        if start >= len(self._raw_value):
            return
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
            index = self._raw_index_from_display_position(cursor.position())
            return index, index

        start = self._raw_index_from_display_position(cursor.selectionStart())
        end = self._raw_index_from_display_position(cursor.selectionEnd())
        return min(start, end), max(start, end)

    def _raw_index_from_display_position(self, position: int) -> int:
        display = self.toPlainText()
        compact_before_cursor = sum(
            1
            for char in display[:max(0, min(position, len(display)))]
            if not char.isspace()
        )
        padding_len = self._display_padding_len()
        return max(0, min(len(self._raw_value), compact_before_cursor - padding_len))

    def _set_cursor_from_raw_index(self, raw_index: int) -> None:
        display_position = self._display_position_from_raw_index(raw_index)
        cursor = self.textCursor()
        cursor.setPosition(display_position)
        self.setTextCursor(cursor)

    def _display_position_from_raw_index(self, raw_index: int) -> int:
        target_compact_index = self._display_padding_len() + max(
            0,
            min(raw_index, len(self._raw_value)),
        )
        compact_count = 0
        for position, char in enumerate(self.toPlainText()):
            if char.isspace():
                continue
            if compact_count >= target_compact_index:
                return position
            compact_count += 1
        return len(self.toPlainText())

    def _display_padding_len(self) -> int:
        compact = "".join(self.toPlainText().split())
        if self._raw_value and compact.endswith(self._raw_value):
            return len(compact) - len(self._raw_value)
        return max(0, len(compact) - len(self._raw_value))

    def _is_valid_char(self, char: str) -> bool:
        if self.input_type == "decimal":
            return char.isdigit()
        if self.input_type == "binary":
            return char in {"0", "1"}
        return char.upper() in {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "A", "B", "C", "D", "E", "F"}

    def _normalize_char(self, char: str) -> str:
        return char.upper() if self.input_type in ("hexBE", "hexLE") else char

    def _within_limit(self, value: str) -> bool:
        if self.input_type == "decimal":
            if not value:
                return True
            return max(1, (int(value).bit_length() + 7) // 8) <= MAX_BYTE_LENGTH
        if self.input_type == "binary":
            return len(value) <= (MAX_BYTE_LENGTH * 8)
        return len(value) <= (MAX_BYTE_LENGTH * 2)

    def _move_cursor_to_end(self) -> None:
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)


class ConverterPanel(QFrame):
    inputEdited = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.inputs: dict[str, ConverterInputEdit] = {}
        self.copy_raw_buttons: dict[str, QToolButton] = {}

        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(20)

        kinds = {
            "decimal": "Decimal",
            "binary": "Binary",
            "hexBE": "Hex (BE)",
            "hexLE": "Hex (LE)",
        }

        for kind, label_text in kinds.items():
            row = QHBoxLayout()
            row.setSpacing(10)

            label = QLabel(label_text)
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            label.setFixedWidth(90)

            editor = ConverterInputEdit(kind)
            editor.setObjectName(f"converter-{kind}")
            editor.valueEdited.connect(self.inputEdited.emit)
            self.inputs[kind] = editor

            copy_raw = QToolButton()
            copy_raw.setObjectName("copy-raw")
            copy_raw.setIcon(Icons.copy())
            copy_raw.setToolTip("Copy raw")
            copy_raw.setCursor(Qt.PointingHandCursor)
            copy_raw.clicked.connect(editor.copy_raw_to_clipboard)
            self.copy_raw_buttons[kind] = copy_raw

            row.addWidget(label)
            row.addWidget(editor, 1)
            row.addWidget(copy_raw)
            main.addLayout(row)

    def set_values(self, raw_values: dict[str, str], display_values: dict[str, str]) -> None:
        for key, editor in self.inputs.items():
            editor.set_content(raw_values.get(key, ""), display_values.get(key, ""))
