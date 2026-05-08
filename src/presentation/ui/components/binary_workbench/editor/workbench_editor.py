from __future__ import annotations

from PySide6.QtCore import QPoint, QStringListModel, Qt, QTimer, Signal
from PySide6.QtGui import QCursor, QKeyEvent, QTextCursor
from PySide6.QtWidgets import QCompleter, QPlainTextEdit, QScrollBar, QToolTip, QWidget

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import (
    COMPLETION_TOKEN,
    ROW_BYTES,
    tooltip_values,
)


class WorkbenchEditor(QPlainTextEdit):
    focused = Signal()
    selectAllRequested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._shared_scrollbar: QScrollBar | None = None
        self._completion_model = QStringListModel(self)
        self._completion_items: dict[str, list[str]] = {"label": [], "variable": [], "equate": []}
        self._symbol_tooltips: dict[str, str] = {}
        self._completer = QCompleter(self._completion_model, self)
        self._completer.setWidget(self)
        self._completer.activated.connect(self._insert_completion)
        self._selection_scroll_delta = 0
        self._selection_timer = QTimer(self)
        self._selection_timer.timeout.connect(self._step_selection_scroll)

    def set_shared_scrollbar(self, scrollbar: QScrollBar) -> None:
        self._shared_scrollbar = scrollbar

    def mouseMoveEvent(self, event) -> None:
        super().mouseMoveEvent(event)
        if event.buttons() & Qt.LeftButton:
            self._update_selection_scroll(event.position().toPoint())
            return
        self._show_symbol_tooltip(event)
        self._stop_selection_scroll()

    def mouseReleaseEvent(self, event) -> None:
        self._stop_selection_scroll()
        super().mouseReleaseEvent(event)

    def focusInEvent(self, event) -> None:
        self.focused.emit()
        super().focusInEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_A and event.modifiers() & Qt.ControlModifier:
            self.selectAllRequested.emit()
            event.accept()
            return
        if event.key() == Qt.Key_Tab:
            self.insertPlainText(" " * BINARY_WORKBENCH_LAYOUT.EDITOR_TAB_SPACES)
            event.accept()
            return
        if self._shared_scrollbar is None:
            super().keyPressEvent(event)
            return
        key = event.key()
        block = self.textCursor().blockNumber()
        last_block = max(0, self.document().blockCount() - 1)
        if key == Qt.Key_Down and block >= last_block:
            self._shared_scrollbar.setValue(self._shared_scrollbar.value() + ROW_BYTES)
            QTimer.singleShot(0, lambda: self._move_cursor_to_edge(False))
            event.accept()
            return
        if key == Qt.Key_Up and block <= 0:
            self._shared_scrollbar.setValue(self._shared_scrollbar.value() - ROW_BYTES)
            QTimer.singleShot(0, lambda: self._move_cursor_to_edge(True))
            event.accept()
            return
        super().keyPressEvent(event)
        self._refresh_completions()

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

    def _move_cursor_to_edge(self, top: bool) -> None:
        cursor = self.textCursor()
        block = self.document().firstBlock() if top else self.document().lastBlock()
        cursor.setPosition(block.position())
        self.setTextCursor(cursor)

    def wheelEvent(self, event) -> None:
        if self._shared_scrollbar is None:
            super().wheelEvent(event)
            return
        delta = event.pixelDelta().y()
        if delta == 0:
            delta = (event.angleDelta().y() // BINARY_WORKBENCH_LAYOUT.WHEEL_SCROLL_DIVISOR) * ROW_BYTES
        self._shared_scrollbar.setValue(self._shared_scrollbar.value() - delta)
        event.accept()

    def leaveEvent(self, event) -> None:
        if not (self.textCursor().hasSelection() and self.hasFocus()):
            self._stop_selection_scroll()
        super().leaveEvent(event)

    def _update_selection_scroll(self, position: QPoint) -> None:
        threshold = 18
        if position.y() < threshold:
            self._selection_scroll_delta = -ROW_BYTES
        elif position.y() > self.viewport().height() - threshold:
            self._selection_scroll_delta = ROW_BYTES
        else:
            self._stop_selection_scroll()
            return
        if not self._selection_timer.isActive():
            self._selection_timer.start(20)

    def _stop_selection_scroll(self) -> None:
        self._selection_scroll_delta = 0
        self._selection_timer.stop()

    def _step_selection_scroll(self) -> None:
        if self._shared_scrollbar is None or self._selection_scroll_delta == 0:
            self._stop_selection_scroll()
            return
        self._shared_scrollbar.setValue(self._shared_scrollbar.value() + self._selection_scroll_delta)
        position = self.viewport().mapFromGlobal(QCursor.pos())
        cursor = self.cursorForPosition(QPoint(max(position.x(), 0), max(position.y(), 0)))
        selection = self.textCursor()
        anchor = selection.anchor()
        selection.setPosition(anchor)
        selection.setPosition(cursor.position(), QTextCursor.KeepAnchor)
        self.setTextCursor(selection)

    def _refresh_completions(self) -> None:
        prefix = self._current_completion_prefix()
        candidates = self._candidates_for_prefix(prefix)
        if not prefix or not candidates:
            self._completer.popup().hide()
            return
        self._completion_model.setStringList(candidates)
        self._completer.setCompletionPrefix(prefix)
        self._completer.complete(self.cursorRect())

    def _current_completion_prefix(self) -> str:
        cursor = self.textCursor()
        block = cursor.block().text()
        column = cursor.positionInBlock()
        for match in COMPLETION_TOKEN.finditer(block):
            if match.start() <= column <= match.end():
                return block[match.start() : column]
        return ""

    def _candidates_for_prefix(self, prefix: str) -> list[str]:
        if prefix.startswith("_"):
            return [item for item in self._completion_items["variable"] if item.startswith(prefix)]
        if prefix.startswith("@"):
            return [item for item in self._completion_items["equate"] if item.startswith(prefix)]
        return [item for item in self._completion_items["label"] if item.startswith(prefix)]

    def _insert_completion(self, completion: str) -> None:
        prefix = self._current_completion_prefix()
        cursor = self.textCursor()
        for _ in prefix:
            cursor.deletePreviousChar()
        cursor.insertText(completion)
        self.setTextCursor(cursor)

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
