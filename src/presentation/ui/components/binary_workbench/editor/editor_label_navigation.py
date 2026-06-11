from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QTextCursor

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT
from src.presentation.ui.components.binary_workbench.editor.cursor_guard import (
    set_cursor_position,
)
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import (
    COMPLETION_TOKEN,
    safe_int,
)


class EditorLabelNavigationMixin:
    def set_label_offsets(self, labels: dict[str, str]) -> None:
        self._label_offsets = {
            name.lower(): (name, safe_int(offset))
            for name, offset in labels.items()
        }

    def _label_at_position(self, position: QPoint) -> tuple[str, int] | None:
        return self._label_offsets.get(self._strict_token_at_position(position).lower())

    def _strict_token_at_position(self, position: QPoint) -> str:
        block = self.cursorForPosition(position).block()
        for match in COMPLETION_TOKEN.finditer(block.text()):
            if self._token_contains_x(block, match.start(), match.end(), position.x()):
                return match.group()
        return ""

    def _token_contains_x(self, block, start: int, end: int, x: int) -> bool:
        cursor = QTextCursor(block)
        set_cursor_position(cursor, block.position() + start)
        left = self.cursorRect(cursor).left()
        set_cursor_position(cursor, block.position() + end)
        right = self.cursorRect(cursor).left()
        margin = BINARY_WORKBENCH_LAYOUT.EDITOR_LABEL_CLICK_MARGIN
        return left - margin <= x <= right + margin

    def _update_label_cursor(self, position: QPoint) -> None:
        cursor = Qt.PointingHandCursor if self._label_at_position(position) else Qt.IBeamCursor
        self.viewport().setCursor(cursor)

    def mousePressEvent(self, event) -> None:
        self._pressed_label = self._label_at_position(event.position().toPoint())
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._stop_selection_scroll()
        super().mouseReleaseEvent(event)
        label = self._label_at_position(event.position().toPoint())
        if event.button() == Qt.LeftButton and label is not None and label == self._pressed_label:
            self.labelActivated.emit(label[1])
        if event.button() == Qt.LeftButton:
            self._show_symbol_tooltip(event)
        self._pressed_label = None
