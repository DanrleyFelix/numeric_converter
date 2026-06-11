from PySide6.QtGui import QTextCursor


def set_cursor_position(
    cursor: QTextCursor,
    position: int,
    mode=QTextCursor.MoveAnchor,
) -> None:
    cursor.setPosition(_clamped_position(cursor, position), mode)


def _clamped_position(cursor: QTextCursor, position: int) -> int:
    document = cursor.document()
    if document is None:
        return max(0, position)
    maximum = max(0, document.characterCount() - 1)
    return min(max(0, position), maximum)
