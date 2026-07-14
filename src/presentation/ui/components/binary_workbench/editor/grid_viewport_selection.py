from PySide6.QtGui import QTextCursor

from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.editor.cursor_guard import (
    set_cursor_position,
)


class GridViewportSelectionMixin:
    """Preserve manual selections by absolute source line across viewports."""

    def _capture_viewport_line_selection(self, preferred_editor=None) -> None:
        if not self._virtual:
            return
        candidates = self._viewport_selection_editors()
        selected = [item for item in candidates if item[1].textCursor().hasSelection()]
        if preferred_editor is not None:
            selected.sort(key=lambda item: item[1] is not preferred_editor)
        elif selected:
            selected.sort(key=lambda item: not item[1].hasFocus())
        if not selected:
            return
        key, editor = selected[0]
        cursor = editor.textCursor()
        anchor_line, anchor_column = self._absolute_line_position(editor, cursor.anchor())
        cursor_line, cursor_column = self._absolute_line_position(editor, cursor.position())
        self._viewport_line_selection = (
            key,
            anchor_line,
            anchor_column,
            cursor_line,
            cursor_column,
        )
        self._virtual_selection_scrolling = True
        kind = self._editor_kind_for_selection(editor)
        if kind is not None:
            anchor_offset = self._offset_for_editor_position(editor, cursor.anchor())
            cursor_offset = self._offset_for_editor_position(editor, cursor.position())
            self._virtual_selection_anchor = anchor_offset
            self._virtual_selection_kind = kind
            self._virtual_selection_range = (kind, anchor_offset, cursor_offset)

    def _restore_viewport_line_selection(self) -> bool:
        if not self._virtual or self._viewport_line_selection is None:
            return False
        key, anchor_line, anchor_column, cursor_line, cursor_column = self._viewport_line_selection
        editor = self._viewport_editor_for_key(key)
        if editor is None:
            return False
        self._virtual_selection_scrolling = True
        for _, candidate in self._viewport_selection_editors():
            if candidate is not editor:
                self._clear_local_selection(candidate)
        first_line = self._visible_line_base()
        last_line = first_line + max(0, editor.document().blockCount() - 1)
        if max(anchor_line, cursor_line) < first_line or min(anchor_line, cursor_line) > last_line:
            self._clear_local_selection(editor)
            self._virtual_selection_scrolling = False
            return True
        cursor = editor.textCursor()
        set_cursor_position(
            cursor,
            self._visible_line_position(editor, anchor_line, anchor_column, first_line, last_line),
        )
        set_cursor_position(
            cursor,
            self._visible_line_position(editor, cursor_line, cursor_column, first_line, last_line),
            QTextCursor.KeepAnchor,
        )
        editor.setTextCursor(cursor)
        editor.verticalScrollBar().setValue(0)
        self._virtual_selection_scrolling = False
        return True

    def _absolute_line_position(self, editor, position: int) -> tuple[int, int]:
        block = editor.document().findBlock(position)
        return self._visible_line_base() + block.blockNumber(), position - block.position()

    def _update_viewport_line_selection_cursor(self, editor, position: int) -> bool:
        if self._viewport_line_selection is None:
            return False
        key, anchor_line, anchor_column, _, _ = self._viewport_line_selection
        if self._viewport_editor_for_key(key) is not editor:
            return False
        cursor_line, cursor_column = self._absolute_line_position(editor, position)
        self._viewport_line_selection = (
            key,
            anchor_line,
            anchor_column,
            cursor_line,
            cursor_column,
        )
        return True

    def _visible_line_position(
        self,
        editor,
        line: int,
        column: int,
        first_line: int,
        last_line: int,
    ) -> int:
        local_line = min(max(line, first_line), last_line) - first_line
        block = editor.document().findBlockByNumber(local_line)
        if line < first_line:
            return block.position()
        if line > last_line:
            return block.position() + len(block.text())
        return block.position() + min(max(0, column), len(block.text()))

    def _visible_line_base(self) -> int:
        for index in range(len(self._rows)):
            offset = self._row_offset(index)
            if offset is not None:
                return (offset // ROW_BYTES) - index
        return self._visible_start_offset // ROW_BYTES

    def _viewport_selection_editors(self):
        return (
            *((f"offset:{name}", editor) for name, editor in self._offset_editors.items()),
            (BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS, self.raw_instructions),
            (BINARY_WORKBENCH_TEXT.BYTES, self.bytes),
            (BINARY_WORKBENCH_TEXT.INSTRUCTION, self.instructions),
        )

    def _viewport_editor_for_key(self, key: str):
        if key.startswith("offset:"):
            return self._offset_editors.get(key.removeprefix("offset:"))
        return self._editor_for_selection_kind(key)

    def _clear_local_selection(self, editor) -> None:
        cursor = editor.textCursor()
        if cursor.hasSelection():
            cursor.clearSelection()
            editor.setTextCursor(cursor)
