import re

from PySide6.QtCore import QPoint, QTimer
from PySide6.QtWidgets import QToolTip

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT
from src.presentation.ui.components.binary_workbench.editor.cursor_guard import (
    set_cursor_position,
)
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import (
    COMPLETION_TOKEN,
    tooltip_values,
)
from src.presentation.ui.components.binary_workbench.editor.debugger.highlighting import (
    DEBUGGER_DIRECTIVE_ERRORS_PROPERTY,
)
from src.presentation.ui.helpers.completer_popup import fit_completer_popup_height


class EditorCompletionMixin:
    def set_symbol_helpers(
        self,
        labels: dict[str, str],
        variables: dict[str, str],
        equates: dict[str, str],
    ) -> None:
        self.set_label_helpers(labels)
        self._completion_items = {
            **self._completion_items,
            "variable": sorted(f"_{name.lstrip('_')}" for name in variables),
            "equate": sorted(f"@{name.lstrip('@')}" for name in equates),
        }
        self._symbol_tooltips = {
            **tooltip_values({f"_{name.lstrip('_')}".lower(): value for name, value in variables.items()}),
            **tooltip_values({f"@{name.lstrip('@')}".lower(): value for name, value in equates.items()}),
        }

    def set_label_helpers(self, labels: dict[str, str]) -> None:
        """Refresh label-only completion state without rebuilding Symbol catalogs."""

        self.set_label_offsets(labels)
        self._completion_items = {
            **self._completion_items,
            "label": sorted(labels),
        }

    def _refresh_completions(self) -> None:
        if (
            getattr(self, "_completion_popup_suppressed", False)
            or getattr(self, "_completion_navigation_timer", None) is not None
            and self._completion_navigation_timer.isActive()
        ):
            self.hide_completion_popup()
            return
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
        fit_completer_popup_height(self._completer)

    def _debounce_completions_after_navigation(self) -> None:
        self.hide_completion_popup()
        self._completion_navigation_timer.start()

    def _current_completion_prefix(self) -> str:
        cursor = self.textCursor()
        block = cursor.block().text()
        column = cursor.positionInBlock()
        directive_prefix = block[:column].lstrip()
        if directive_prefix.startswith("*") and re.fullmatch(
            r"\*\s*[A-Za-z_]*",
            directive_prefix,
        ):
            return directive_prefix
        for match in COMPLETION_TOKEN.finditer(block):
            if match.start() <= column <= match.end():
                return block[match.start() : column]
        return ""

    def _candidates_for_prefix(self, prefix: str) -> list[str]:
        normalized = prefix.lower()
        if normalized.startswith("*"):
            command = normalized[1:].strip()
            return [
                f"* {name}"
                for name in _partial_prefix_matches(
                    self._completion_items["directive"],
                    command,
                )
            ]
        if normalized.startswith("/"):
            return _partial_prefix_matches(self._completion_items["command"], normalized)
        if normalized.startswith("_"):
            return _partial_prefix_matches(self._completion_items["variable"], normalized)
        if normalized.startswith("@"):
            return _partial_prefix_matches(self._completion_items["equate"], normalized)
        return _partial_prefix_matches(self._completion_items["label"], normalized)

    def _accept_current_completion(self) -> bool:
        popup = self._completer.popup()
        if not popup.isVisible():
            return False
        completion = popup.currentIndex().data()
        if completion is None:
            completion = _first_completion(self._completion_model.stringList())
        if not completion:
            return False
        popup.hide()
        self._insert_completion(str(completion))
        self.setFocus()
        return True

    def _completion_popup_width(self) -> int:
        popup = self._completer.popup()
        content_width = popup.sizeHintForColumn(0)
        padded_width = (
            content_width
            + BINARY_WORKBENCH_LAYOUT.EDITOR_COMPLETION_WIDTH_PADDING
        )
        return max(BINARY_WORKBENCH_LAYOUT.EDITOR_COMPLETION_MIN_WIDTH, padded_width)

    def _insert_completion(self, completion: str) -> None:
        if self._completion_cursor_position is not None:
            cursor = self.textCursor()
            set_cursor_position(cursor, self._completion_cursor_position)
            self.setTextCursor(cursor)
        prefix = self._current_completion_prefix()
        cursor = self.textCursor()
        position = cursor.position() - len(prefix) + len(completion)
        cursor.beginEditBlock()
        for _ in prefix:
            cursor.deletePreviousChar()
        cursor.insertText(completion)
        cursor.endEditBlock()
        self.setTextCursor(cursor)
        self._completion_cursor_position = None
        self._restore_completion_cursor(position)
        QTimer.singleShot(0, lambda: self._restore_completion_cursor(position))

    def set_command_completions(self, commands: list[str]) -> None:
        self._completion_items = {**self._completion_items, "command": sorted(commands)}

    def _restore_completion_cursor(self, position: int) -> None:
        cursor = self.textCursor()
        set_cursor_position(cursor, position)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def _show_symbol_tooltip(self, event) -> None:
        cursor = self.cursorForPosition(event.position().toPoint())
        errors = self.document().property(DEBUGGER_DIRECTIVE_ERRORS_PROPERTY)
        message = errors.get(cursor.blockNumber(), "") if isinstance(errors, dict) else ""
        if message:
            QToolTip.showText(event.globalPosition().toPoint(), message, self)
            return
        token = self._symbol_token_at_position(event.position().toPoint())
        text = self._symbol_tooltips.get(token)
        if text:
            QToolTip.showText(event.globalPosition().toPoint(), text, self)
            return
        QToolTip.hideText()

    def _symbol_token_at_position(self, position: QPoint) -> str:
        token = self._strict_token_at_position(position).lower()
        return token if token in self._symbol_tooltips else ""

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


def _partial_prefix_matches(values: list[str], normalized_prefix: str) -> list[str]:
    return [
        item
        for item in values
        if item.lower().startswith(normalized_prefix)
        and item.lower() != normalized_prefix
    ]
