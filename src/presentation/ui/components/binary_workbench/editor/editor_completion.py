from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QToolTip

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import (
    COMPLETION_TOKEN,
    tooltip_values,
)


class EditorCompletionMixin:
    def set_symbol_helpers(
        self,
        labels: dict[str, str],
        variables: dict[str, str],
        equates: dict[str, str],
    ) -> None:
        self._completion_items = {
            "label": sorted(labels),
            "variable": sorted(f"_{name.lstrip('_')}" for name in variables),
            "equate": sorted(f"@{name.lstrip('@')}" for name in equates),
        }
        self._symbol_tooltips = {
            **tooltip_values(labels),
            **tooltip_values({f"_{name.lstrip('_')}": value for name, value in variables.items()}),
            **tooltip_values({f"@{name.lstrip('@')}": value for name, value in equates.items()}),
        }

    def _refresh_completions(self) -> None:
        prefix = self._current_completion_prefix()
        candidates = self._candidates_for_prefix(prefix)
        if not prefix or not candidates:
            self._completion_cursor_position = None
            self._completer.popup().hide()
            return
        self._completion_cursor_position = self.textCursor().position()
        self._completion_model.setStringList(candidates)
        self._completer.setCompletionPrefix(prefix)
        popup = self._completer.popup()
        popup.setCurrentIndex(self._completer.completionModel().index(0, 0))
        rect = self.cursorRect()
        rect.translate(
            0,
            self.fontMetrics().height() + BINARY_WORKBENCH_LAYOUT.EDITOR_COMPLETION_VERTICAL_OFFSET,
        )
        rect.setWidth(self._completion_popup_width())
        self._completer.complete(rect)

    def _current_completion_prefix(self) -> str:
        cursor = self.textCursor()
        block = cursor.block().text()
        column = cursor.positionInBlock()
        for match in COMPLETION_TOKEN.finditer(block):
            if match.start() <= column <= match.end():
                return block[match.start() : column]
        return ""

    def _candidates_for_prefix(self, prefix: str) -> list[str]:
        normalized = prefix.lower()
        if normalized.startswith("_"):
            return [item for item in self._completion_items["variable"] if item.lower().startswith(normalized)]
        if normalized.startswith("@"):
            return [item for item in self._completion_items["equate"] if item.lower().startswith(normalized)]
        return [item for item in self._completion_items["label"] if item.lower().startswith(normalized)]

    def _accept_current_completion(self) -> bool:
        popup = self._completer.popup()
        if not popup.isVisible():
            return False
        completion = popup.currentIndex().data()
        if completion is None:
            completion = _first_completion(self._completion_model.stringList())
        if not completion:
            return False
        self._insert_completion(str(completion))
        self._completion_cursor_position = None
        popup.hide()
        return True

    def _completion_popup_width(self) -> int:
        popup = self._completer.popup()
        content_width = popup.sizeHintForColumn(0)
        scrollbar_width = popup.verticalScrollBar().sizeHint().width()
        padded_width = (
            content_width
            + scrollbar_width
            + BINARY_WORKBENCH_LAYOUT.EDITOR_COMPLETION_WIDTH_PADDING
        )
        return max(BINARY_WORKBENCH_LAYOUT.EDITOR_COMPLETION_MIN_WIDTH, padded_width)

    def _insert_completion(self, completion: str) -> None:
        if self._completion_cursor_position is not None:
            cursor = self.textCursor()
            cursor.setPosition(self._completion_cursor_position)
            self.setTextCursor(cursor)
        prefix = self._current_completion_prefix()
        cursor = self.textCursor()
        for _ in prefix:
            cursor.deletePreviousChar()
        cursor.insertText(completion)
        self.setTextCursor(cursor)
        self._completion_cursor_position = None

    def _show_symbol_tooltip(self, event) -> None:
        text = self._symbol_tooltips.get(self._token_at_position(event.position().toPoint()))
        if text:
            QToolTip.showText(event.globalPosition().toPoint(), text, self)
            return
        QToolTip.hideText()

    def _token_at_position(self, position: QPoint) -> str:
        cursor = self.cursorForPosition(position)
        block = cursor.block().text()
        column = cursor.positionInBlock()
        for match in COMPLETION_TOKEN.finditer(block):
            if match.start() <= column <= match.end():
                return match.group()
        return ""


def _first_completion(values: list[str]) -> str:
    return values[0] if values else ""
