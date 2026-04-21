from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QTextCursor, QKeySequence
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QPlainTextEdit, QVBoxLayout

from src.core.converter.errors import MAX_BYTE_LENGTH


class ConverterInputEdit(QPlainTextEdit):
    valueEdited = Signal(str, str)

    def __init__(self, input_type: str):
        super().__init__()
        self.input_type = input_type
        self._raw_value = ""
        self.setMinimumHeight(40)
        self.setTabChangesFocus(True)

    @property
    def raw_value(self) -> str:
        return self._raw_value

    def set_content(self, raw_value: str, display_value: str) -> None:
        self._raw_value = raw_value
        self.setPlainText(display_value)
        self._move_cursor_to_end()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.matches(QKeySequence.Copy) or event.matches(QKeySequence.SelectAll):
            super().keyPressEvent(event)
            return

        if event.matches(QKeySequence.Paste):
            self._append_text(QApplication.clipboard().text())
            event.accept()
            return

        if event.key() in (Qt.Key_Backspace, Qt.Key_Delete):
            if self._raw_value:
                self._raw_value = self._raw_value[:-1]
                self.valueEdited.emit(self.input_type, self._raw_value)
            event.accept()
            return

        if event.key() in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down, Qt.Key_Home, Qt.Key_End):
            self._move_cursor_to_end()
            event.accept()
            return

        text = event.text()
        if text and not event.modifiers():
            self._append_text(text)
            event.accept()
            return

        event.accept()

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        self._move_cursor_to_end()

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        self._move_cursor_to_end()

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        self._move_cursor_to_end()

    def _append_text(self, text: str) -> None:
        updated = self._raw_value
        for char in text:
            if not self._is_valid_char(char):
                continue
            candidate = updated + self._normalize_char(char)
            if not self._within_limit(candidate):
                continue
            updated = candidate

        if updated != self._raw_value:
            self._raw_value = updated
            self.valueEdited.emit(self.input_type, self._raw_value)

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
            row.setSpacing(20)

            label = QLabel(label_text)
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            label.setFixedWidth(90)

            editor = ConverterInputEdit(kind)
            editor.setObjectName(f"converter-{kind}")
            editor.valueEdited.connect(self.inputEdited.emit)
            self.inputs[kind] = editor

            row.addWidget(label)
            row.addWidget(editor, 1)
            main.addLayout(row)

    def set_values(self, raw_values: dict[str, str], display_values: dict[str, str]) -> None:
        for key, editor in self.inputs.items():
            editor.set_content(raw_values.get(key, ""), display_values.get(key, ""))
