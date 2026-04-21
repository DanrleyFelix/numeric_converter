import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent, QTextCursor
from PySide6.QtWidgets import QApplication

from src.presentation.ui.components.converter_panel import ConverterInputEdit
from src.presentation.ui.components.key_panel import KeyPanel


_APP = None


def _app() -> QApplication:
    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


def _press(editor: ConverterInputEdit, key: int, text: str = "") -> None:
    event = QKeyEvent(
        QEvent.Type.KeyPress,
        key,
        Qt.KeyboardModifier.NoModifier,
        text,
    )
    editor.keyPressEvent(event)


def test_converter_normal_copy_keeps_display_spacing_and_copy_raw_removes_spaces():
    app = _app()
    editor = ConverterInputEdit("hexLE")
    editor.set_content("45", "00 45")

    editor.selectAll()
    editor.copy()
    assert app.clipboard().text() == "00 45"

    editor.copy_raw_to_clipboard()
    assert app.clipboard().text() == "0045"


def test_converter_select_all_backspace_removes_raw_content():
    _app()
    editor = ConverterInputEdit("hexLE")
    values: list[tuple[str, str]] = []
    editor.valueEdited.connect(lambda kind, value: values.append((kind, value)))
    editor.set_content("45", "00 45")

    editor.selectAll()
    _press(editor, Qt.Key.Key_Backspace)

    assert editor.raw_value == ""
    assert values[-1] == ("hexLE", "")


def test_converter_inserts_at_current_cursor_position():
    _app()
    editor = ConverterInputEdit("hexLE")
    editor.set_content("45", "00 45")

    cursor = editor.textCursor()
    cursor.setPosition(3, QTextCursor.MoveMode.MoveAnchor)
    editor.setTextCursor(cursor)
    _press(editor, Qt.Key.Key_A, "A")

    assert editor.raw_value == "A45"


def test_key_panel_does_not_include_log_key():
    _app()
    panel = KeyPanel()

    assert "LOG" not in panel.buttons
    assert "" not in panel.buttons
