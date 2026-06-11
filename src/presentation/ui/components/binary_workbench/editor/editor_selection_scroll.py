from PySide6.QtCore import QPoint
from PySide6.QtGui import QCursor, QTextCursor

from src.presentation.ui.components.binary_workbench.editor.cursor_guard import (
    set_cursor_position,
)
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import ROW_BYTES

_SELECTION_SCROLL_EDGE_THRESHOLD = 18
_SELECTION_SCROLL_INTERVAL_MS = 20


class EditorSelectionScrollMixin:
    def _update_selection_scroll(self, position: QPoint) -> None:
        if position.y() < _SELECTION_SCROLL_EDGE_THRESHOLD:
            self._selection_scroll_delta = -ROW_BYTES
        elif position.y() > self.viewport().height() - _SELECTION_SCROLL_EDGE_THRESHOLD:
            self._selection_scroll_delta = ROW_BYTES
        else:
            self._stop_selection_scroll()
            return
        if not self._selection_timer.isActive():
            self._selection_timer.start(_SELECTION_SCROLL_INTERVAL_MS)

    def _stop_selection_scroll(self) -> None:
        self._selection_scroll_delta = 0
        self._selection_timer.stop()

    def _step_selection_scroll(self) -> None:
        if self._shared_scrollbar is None or self._selection_scroll_delta == 0:
            self._stop_selection_scroll()
            return
        self.selectionAutoScrollAboutToStep.emit(self)
        self._shared_scrollbar.setValue(self._shared_scrollbar.value() + self._selection_scroll_delta)
        position = self.viewport().mapFromGlobal(QCursor.pos())
        cursor = self.cursorForPosition(QPoint(max(position.x(), 0), max(position.y(), 0)))
        selection = self.textCursor()
        anchor = selection.anchor()
        set_cursor_position(selection, anchor)
        set_cursor_position(selection, cursor.position(), QTextCursor.KeepAnchor)
        self.setTextCursor(selection)
        self.selectionAutoScrolled.emit(self)
