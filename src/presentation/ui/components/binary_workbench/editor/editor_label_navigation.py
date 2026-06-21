import re

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QTextCursor

from src.modules.constants import HEX_DIGIT_PATTERN
from src.modules.contracts import CPUArchCodec
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT
from src.presentation.ui.components.binary_workbench.editor.cursor_guard import (
    set_cursor_position,
)
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import (
    COMPLETION_TOKEN,
    safe_int,
)

JUMP_TARGET_TOKEN = re.compile(rf"[@_]?[A-Za-z_][A-Za-z0-9_]*|[-+]?(?:0x{HEX_DIGIT_PATTERN}+|\d+)")


class EditorLabelNavigationMixin:
    def set_label_offsets(self, labels: dict[str, str]) -> None:
        self._label_offsets = {
            name.lower(): (name, safe_int(offset))
            for name, offset in labels.items()
        }

    def set_jump_navigation(
        self,
        codec: CPUArchCodec,
        variables: dict[str, str],
        equates: dict[str, str],
    ) -> None:
        self._jump_codec = codec
        self._jump_symbols = {
            **{f"_{name.lstrip('_')}".lower(): value for name, value in variables.items()},
            **{f"@{name.lstrip('@')}".lower(): value for name, value in equates.items()},
        }

    def _label_at_position(self, position: QPoint) -> tuple[str, int] | None:
        return self._label_offsets.get(self._strict_token_at_position(position).lower())

    def _jump_target_at_position(self, position: QPoint) -> int | None:
        token = self._strict_token_at_position(position, JUMP_TARGET_TOKEN)
        if not token or self._jump_codec is None:
            return None
        return self._jump_codec.jump_navigation_target(
            self.cursorForPosition(position).block().text(),
            token,
            self._jump_symbols,
        )

    def _navigation_target_at_position(self, position: QPoint) -> int | None:
        label = self._label_at_position(position)
        return label[1] if label is not None else self._jump_target_at_position(position)

    def _strict_token_at_position(
        self,
        position: QPoint,
        pattern: re.Pattern[str] = COMPLETION_TOKEN,
    ) -> str:
        block = self.cursorForPosition(position).block()
        for match in pattern.finditer(block.text()):
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
        cursor = Qt.PointingHandCursor if self._navigation_target_at_position(position) is not None else Qt.IBeamCursor
        self.viewport().setCursor(cursor)

    def mousePressEvent(self, event) -> None:
        self._pressed_navigation_target = self._navigation_target_at_position(event.position().toPoint())
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._stop_selection_scroll()
        super().mouseReleaseEvent(event)
        target = self._navigation_target_at_position(event.position().toPoint())
        if event.button() == Qt.LeftButton and target is not None and target == self._pressed_navigation_target:
            self.labelActivated.emit(target)
        if event.button() == Qt.LeftButton:
            self._show_symbol_tooltip(event)
        self._pressed_navigation_target = None
