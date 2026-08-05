from dataclasses import dataclass

from PySide6.QtGui import QTextCursor


@dataclass(frozen=True)
class LogicalCursorState:
    """Store a cursor by logical row/column instead of fragile character offsets."""

    position_block: int
    position_in_block: int
    anchor_block: int
    anchor_in_block: int


def set_cursor_position(
    cursor: QTextCursor,
    position: int,
    mode=QTextCursor.MoveAnchor,
) -> None:
    cursor.setPosition(_clamped_position(cursor, position), mode)


def capture_logical_cursor(editor) -> LogicalCursorState:
    """Capture an editor cursor so document splices cannot invalidate it."""

    cursor = editor.textCursor()
    document = editor.document()
    anchor_block = document.findBlock(cursor.anchor())
    if not anchor_block.isValid():
        anchor_block = document.lastBlock()
    return LogicalCursorState(
        cursor.blockNumber(),
        cursor.positionInBlock(),
        anchor_block.blockNumber(),
        max(0, cursor.anchor() - anchor_block.position()),
    )


def restore_logical_cursor(editor, state: LogicalCursorState) -> None:
    """Restore a logical cursor, clamping it to the current document shape."""

    document = editor.document()
    last = max(0, document.blockCount() - 1)
    anchor_block = document.findBlockByNumber(min(max(0, state.anchor_block), last))
    position_block = document.findBlockByNumber(
        min(max(0, state.position_block), last)
    )
    cursor = QTextCursor(document)
    set_cursor_position(
        cursor,
        anchor_block.position() + min(state.anchor_in_block, len(anchor_block.text())),
    )
    set_cursor_position(
        cursor,
        position_block.position()
        + min(state.position_in_block, len(position_block.text())),
        QTextCursor.KeepAnchor,
    )
    editor.setTextCursor(cursor)


def _clamped_position(cursor: QTextCursor, position: int) -> int:
    document = cursor.document()
    if document is None:
        return max(0, position)
    maximum = max(0, document.characterCount() - 1)
    return min(max(0, position), maximum)
