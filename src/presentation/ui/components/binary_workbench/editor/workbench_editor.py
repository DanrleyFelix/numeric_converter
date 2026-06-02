from __future__ import annotations

from PySide6.QtCore import QEvent, QStringListModel, Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent, QKeySequence
from PySide6.QtWidgets import QCompleter, QFrame, QListView, QPlainTextEdit, QScrollBar, QWidget

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT
from src.presentation.ui.components.binary_workbench.editor.editor_completion import EditorCompletionMixin
from src.presentation.ui.components.binary_workbench.editor.editor_immediate_menu import (
    EditorImmediateMenuMixin,
)
from src.presentation.ui.components.binary_workbench.editor.editor_label_navigation import (
    EditorLabelNavigationMixin,
)
from src.presentation.ui.components.binary_workbench.editor.editor_selection_scroll import (
    EditorSelectionScrollMixin,
)
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import (
    ROW_BYTES,
)
from src.presentation.ui.helpers.load_qss import STYLESHEET


class WorkbenchEditor(EditorCompletionMixin, EditorImmediateMenuMixin, EditorLabelNavigationMixin, EditorSelectionScrollMixin, QPlainTextEdit):
    focused = Signal()
    selectAllRequested = Signal()
    immediateSymbolRequested = Signal(str, str)
    labelActivated = Signal(int)
    labelOpenTabRequested = Signal(str, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self._shared_scrollbar: QScrollBar | None = None
        self._completion_model = QStringListModel(self)
        self._completion_items: dict[str, list[str]] = {"label": [], "variable": [], "equate": []}
        self._symbol_tooltips: dict[str, str] = {}
        self._label_offsets: dict[str, tuple[str, int]] = {}
        self._completion_cursor_position: int | None = None
        self._immediate_symbol_menu_enabled = False
        self._completer = QCompleter(self._completion_model, self)
        self._completer.setWidget(self)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setCompletionMode(QCompleter.PopupCompletion)
        self._completer.setFilterMode(Qt.MatchStartsWith)
        self._completer.activated.connect(self._insert_completion)
        self._setup_completion_popup()
        self._selection_scroll_delta = 0
        self._selection_timer = QTimer(self)
        self._selection_timer.timeout.connect(self._step_selection_scroll)

    def _setup_completion_popup(self) -> None:
        popup = QListView()
        popup.setObjectName("binary-workbench-completer")
        popup.setStyleSheet(STYLESHEET)
        popup.setFocusPolicy(Qt.NoFocus)
        popup.setFrameShape(QFrame.NoFrame)
        popup.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        popup.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        popup.setUniformItemSizes(True)
        popup.setMouseTracking(True)
        popup.setSpacing(0)
        popup.installEventFilter(self)
        self._completer.setPopup(popup)

    def set_shared_scrollbar(self, scrollbar: QScrollBar) -> None:
        self._shared_scrollbar = scrollbar

    def mouseMoveEvent(self, event) -> None:
        super().mouseMoveEvent(event)
        if event.buttons() & Qt.LeftButton:
            self._update_selection_scroll(event.position().toPoint())
            return
        self._update_label_cursor(event.position().toPoint())
        self._stop_selection_scroll()

    def focusInEvent(self, event) -> None:
        self.focused.emit()
        super().focusInEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.matches(QKeySequence.Undo):
            self.undo()
            event.accept()
            return
        if event.matches(QKeySequence.Redo) or (
            event.key() == Qt.Key_Z
            and bool(event.modifiers() & Qt.ControlModifier)
            and bool(event.modifiers() & Qt.ShiftModifier)
        ):
            self.redo()
            event.accept()
            return
        if event.key() in {Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab} and self._accept_current_completion():
            event.accept()
            return
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
            self._refresh_completions()
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
        self.viewport().setCursor(Qt.IBeamCursor)
        if not (self.textCursor().hasSelection() and self.hasFocus()):
            self._stop_selection_scroll()
        super().leaveEvent(event)

    def eventFilter(self, watched, event) -> bool:
        popup = self._completer.popup()
        if watched is popup and event.type() == QEvent.Type.KeyPress:
            if event.key() in {Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab}:
                self._accept_current_completion()
                event.accept()
                return True
            if event.key() == Qt.Key_Escape:
                popup.hide()
                event.accept()
                return True
        return super().eventFilter(watched, event)
