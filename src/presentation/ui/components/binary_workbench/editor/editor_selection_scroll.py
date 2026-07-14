from PySide6.QtCore import QPoint
from PySide6.QtGui import QCursor, QTextCursor

from src.presentation.ui.components.binary_workbench.editor.cursor_guard import (
    set_cursor_position,
)
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES

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
        position = self.viewport().mapFromGlobal(QCursor.pos())
        self._extend_selection_viewport(self._selection_scroll_delta, position)

    def _extend_selection_viewport(
        self,
        delta: int,
        position: QPoint | None = None,
    ) -> None:
        if self._shared_scrollbar is None or delta == 0:
            return
        self.selectionAutoScrollAboutToStep.emit(self)
        previous = self._shared_scrollbar.value()
        self._shared_scrollbar.setValue(previous + delta)
        if self._shared_scrollbar.value() == previous:
            self.selectionAutoScrolled.emit(self)
            return
        if position is None:
            position = QPoint(
                self.cursorRect().center().x(),
                self.viewport().height() - 1 if delta > 0 else 0,
            )
        else:
            position = QPoint(
                max(0, min(position.x(), self.viewport().width() - 1)),
                self.viewport().height() - 1 if delta > 0 else 0,
            )
        cursor = self.cursorForPosition(position)
        selection = self.textCursor()
        anchor = selection.anchor()
        set_cursor_position(selection, anchor)
        set_cursor_position(selection, cursor.position(), QTextCursor.KeepAnchor)
        self.setTextCursor(selection)
        self.selectionAutoScrolled.emit(self)
