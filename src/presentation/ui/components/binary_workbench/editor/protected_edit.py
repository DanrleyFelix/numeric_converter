from PySide6.QtGui import QTextCursor

from src.presentation.ui.components.binary_workbench.editor.cursor_guard import (
    set_cursor_position,
)


def replace_selection_preserving_line_breaks(
    editor,
    cursor: QTextCursor,
    prefix: str = "",
) -> None:
    start = cursor.selectionStart()
    end = cursor.selectionEnd()
    first_block = editor.document().findBlock(start)
    if first_block.isValid():
        end = min(end, first_block.position() + len(first_block.text()))
    was_granular = bool(getattr(editor, "_granular_editing", False))
    editor._granular_editing = True
    try:
        cursor.beginEditBlock()
        try:
            set_cursor_position(cursor, start)
            set_cursor_position(cursor, end, QTextCursor.KeepAnchor)
            cursor.insertText(prefix)
        finally:
            cursor.endEditBlock()
    finally:
        editor._granular_editing = was_granular
    set_cursor_position(cursor, start + len(prefix))
    editor.setTextCursor(cursor)


def remove_editor_block(editor, row: int) -> bool:
    block = editor.document().findBlockByNumber(row)
    if not block.isValid():
        return False
    cursor = editor.textCursor()
    start = block.position()
    end = block.position() + len(block.text())
    if block.next().isValid():
        end = block.next().position()
    elif block.previous().isValid():
        start = max(0, start - 1)
    cursor.beginEditBlock()
    set_cursor_position(cursor, start)
    set_cursor_position(cursor, end, QTextCursor.KeepAnchor)
    cursor.removeSelectedText()
    cursor.endEditBlock()
    editor.setTextCursor(cursor)
    return True
