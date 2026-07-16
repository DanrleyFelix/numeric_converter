from __future__ import annotations

from PySide6.QtCore import QEvent, QSignalBlocker, QStringListModel, Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent, QKeySequence, QPainter, QTextCursor
from PySide6.QtWidgets import QCompleter, QFrame, QListView, QPlainTextEdit, QScrollBar, QWidget

from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES
from src.modules.constants import HEX_DIGITS
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TIMING,
)
from src.presentation.ui.components.binary_workbench.editor.editor_completion import EditorCompletionMixin
from src.presentation.ui.components.binary_workbench.editor.editor_granular_undo import (
    EditorGranularUndoMixin,
)
from src.presentation.ui.components.binary_workbench.editor.editor_immediate_menu import (
    EditorImmediateMenuMixin,
)
from src.presentation.ui.components.binary_workbench.editor.editor_label_navigation import (
    EditorLabelNavigationMixin,
)
from src.presentation.ui.components.binary_workbench.editor.editor_label_folding import (
    EditorLabelFoldingMixin,
)
from src.presentation.ui.components.binary_workbench.editor.editor_selection_scroll import (
    EditorSelectionScrollMixin,
)
from src.presentation.ui.components.binary_workbench.editor.editor_shortcuts import (
    EditorShortcutMixin,
)
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import (
    normalize_instruction_text,
)
from src.presentation.ui.components.binary_workbench.editor.cursor_guard import (
    set_cursor_position,
)
from src.presentation.ui.helpers.load_qss import STYLESHEET


_COMPLETION_NAVIGATION_KEYS = {
    Qt.Key_Up,
    Qt.Key_Down,
    Qt.Key_Left,
    Qt.Key_Right,
}


class WorkbenchEditor(
    EditorCompletionMixin,
    EditorImmediateMenuMixin,
    EditorLabelNavigationMixin,
    EditorLabelFoldingMixin,
    EditorSelectionScrollMixin,
    EditorShortcutMixin,
    EditorGranularUndoMixin,
    QPlainTextEdit,
):
    focused = Signal()
    selectAllRequested = Signal()
    immediateSymbolRequested = Signal(str, str, int, int)
    symbolEditRequested = Signal(str)
    labelActivated = Signal(int)
    jumpNavigationActivated = Signal(int, int)
    labelOpenTabRequested = Signal(str, int)
    addCommandRequested = Signal(str, str)
    copyRequested = Signal(object)
    selectionStarted = Signal(object)
    selectionAutoScrollAboutToStep = Signal(object)
    selectionAutoScrolled = Signal(object)
    viewportChangeAboutToStart = Signal(object)
    viewportChangeFinished = Signal(object)
    returnKeyPressed = Signal(object, object)
    protectedEditKeyPressed = Signal(object, object)
    navigationWarningRequested = Signal(str)
    labelFoldToggled = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self._shared_scrollbar: QScrollBar | None = None
        self._completion_model = QStringListModel(self)
        self._completion_items: dict[str, list[str]] = {"label": [], "variable": [], "equate": [], "command": []}
        self._symbol_tooltips: dict[str, str] = {}
        self._pressed_symbol_token = ""
        self._label_offsets: dict[str, tuple[str, int]] = {}
        self._label_target_resolver = None
        self._jump_label_symbols: set[str] = set()
        self._jump_codec = None
        self._jump_symbols: dict[str, str] = {}
        self._jump_symbol_kinds: dict[str, str] = {}
        self._hex_input_enabled = False
        self._uppercase_hex_input = False
        self._uppercase_instruction_cursor = False
        self._last_instruction_cursor_block: int | None = None
        self._normalizing_instruction_line = False
        self._editor_extra_selections = []
        self._hazard_extra_selections = []
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
        self._left_mouse_selecting = False
        self._return_key_handled = False
        self._protected_edit_key_handled = False
        self._selection_timer = QTimer(self)
        self._selection_timer.timeout.connect(self._step_selection_scroll)
        self._completion_navigation_timer = QTimer(self)
        self._completion_navigation_timer.setSingleShot(True)
        self._completion_navigation_timer.setInterval(
            BINARY_WORKBENCH_TIMING.EDITOR_COMPLETION_NAVIGATION_DEBOUNCE_MS
        )
        self._completion_navigation_timer.timeout.connect(self._refresh_completions)
        self._setup_label_folding()
        self.setup_editor_shortcuts()
        self.cursorPositionChanged.connect(self._normalize_instruction_line_after_offset_change)

    def _setup_completion_popup(self) -> None:
        popup = QListView()
        popup.setObjectName("binary-workbench-completer")
        popup.setStyleSheet(STYLESHEET)
        popup.setFocusPolicy(Qt.NoFocus)
        popup.setFrameShape(QFrame.NoFrame)
        popup.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        popup.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        popup.setUniformItemSizes(True)
        popup.setMouseTracking(True)
        popup.setSpacing(0)
        popup.installEventFilter(self)
        popup.viewport().installEventFilter(self)
        self._completer.setPopup(popup)
        self.installEventFilter(self)

    def setExtraSelections(self, selections) -> None:
        self._editor_extra_selections = list(selections)
        self._sync_extra_selections()

    def set_hazard_extra_selections(self, selections) -> None:
        self._hazard_extra_selections = list(selections)
        self._sync_extra_selections()

    def _sync_extra_selections(self) -> None:
        super().setExtraSelections([*self._hazard_extra_selections, *self._editor_extra_selections])

    def set_shared_scrollbar(self, scrollbar: QScrollBar) -> None:
        self._shared_scrollbar = scrollbar

    def set_hex_input_mode(self, enabled: bool, uppercase: bool) -> None:
        self._hex_input_enabled = enabled
        self._uppercase_hex_input = uppercase

    def set_uppercase_hex_input(self, enabled: bool) -> None:
        self.set_hex_input_mode(True, enabled)

    def set_uppercase_instruction_hover(self, enabled: bool) -> None:
        self._uppercase_instruction_cursor = enabled
        self._last_instruction_cursor_block = self.textCursor().blockNumber()

    def set_completion_popup_suppressed(self, enabled: bool) -> None:
        self._completion_popup_suppressed = enabled
        if enabled:
            self.hide_completion_popup()

    def completion_popup_suppressed(self) -> bool:
        return self._completion_popup_suppressed

    def hide_completion_popup(self) -> None:
        self._completion_cursor_position = None
        self._completer.popup().hide()

    def mouseMoveEvent(self, event) -> None:
        super().mouseMoveEvent(event)
        if event.buttons() & Qt.LeftButton:
            self._update_selection_scroll(event.position().toPoint())
            return
        position = event.position().toPoint()
        self._update_label_cursor(position)
        self._stop_selection_scroll()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._left_mouse_selecting = True
            self._pressed_symbol_token = self._symbol_token_at_position(
                event.position().toPoint()
            )
        if self.handle_alt_click_multicursor(event):
            self._pressed_symbol_token = ""
            self.selectionStarted.emit(self)
            event.accept()
            return
        self.clear_editor_occurrence_selection()
        self.selectionStarted.emit(self)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        position = event.position().toPoint()
        symbol = self._symbol_token_at_position(position)
        edit_symbol = (
            symbol
            and symbol == self._pressed_symbol_token
            and (
                self._navigation_target_at_position(position) is None
                or bool(event.modifiers() & Qt.ControlModifier)
            )
        )
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton:
            self._left_mouse_selecting = False
            self._pressed_symbol_token = ""
            if edit_symbol:
                self.symbolEditRequested.emit(symbol.lstrip("_@"))

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if not self.has_multicursor_ranges():
            return
        painter = QPainter(self.viewport())
        color = self.palette().highlight().color()
        width = max(2, self.cursorWidth())
        for position in self.multicursor_positions():
            cursor = QTextCursor(self.document())
            set_cursor_position(cursor, position)
            rect = self.cursorRect(cursor)
            painter.fillRect(rect.x(), rect.y(), width, rect.height(), color)

    def focusInEvent(self, event) -> None:
        self.focused.emit()
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:
        self.clear_editor_occurrence_selection()
        cursor = self.textCursor()
        if cursor.hasSelection():
            cursor.clearSelection()
            self.setTextCursor(cursor)
        self._stop_selection_scroll()
        super().focusOutEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in _COMPLETION_NAVIGATION_KEYS:
            self._debounce_completions_after_navigation()
        if self.handle_immediate_symbol_shortcut(event.key(), event.modifiers()):
            event.accept()
            return
        if self.handle_editor_shortcut(event):
            event.accept()
            return
        if event.matches(QKeySequence.Copy):
            self.copyRequested.emit(self)
            event.accept()
            return
        if event.matches(QKeySequence.Undo):
            self.clear_editor_occurrence_selection()
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
        if event.matches(QKeySequence.SelectAll):
            self.selectAllRequested.emit()
            event.accept()
            return
        if event.key() in {Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab} and self._accept_current_completion():
            event.accept()
            return
        if event.key() in {Qt.Key_Return, Qt.Key_Enter}:
            self._return_key_handled = False
            self.returnKeyPressed.emit(self, event)
            if self._return_key_handled:
                event.accept()
                return
        if self._is_instruction_editor() and _alt_shortcut_event(event):
            self._completer.popup().hide()
            event.ignore()
            return
        if event.key() in {Qt.Key_Backspace, Qt.Key_Delete}:
            self._protected_edit_key_handled = False
            self.protectedEditKeyPressed.emit(self, event)
            if self._protected_edit_key_handled:
                event.accept()
                return
        filtered_event = self._hex_text_event(event)
        if filtered_event is None:
            event.accept()
            return
        event = filtered_event
        if self.handle_granular_text_edit(event):
            self._refresh_completions()
            self._normalize_instruction_after_comment_start(event.text())
            event.accept()
            return
        if event.key() == Qt.Key_Tab:
            self.insertPlainText(" " * BINARY_WORKBENCH_LAYOUT.EDITOR_TAB_SPACES)
            event.accept()
            return
        if self._shared_scrollbar is None:
            super().keyPressEvent(event)
            self._refresh_completions()
            self._normalize_instruction_after_comment_start(event.text())
            return
        key = event.key()
        if key in {Qt.Key_PageUp, Qt.Key_PageDown}:
            page = max(ROW_BYTES, self._shared_scrollbar.pageStep())
            delta = -page if key == Qt.Key_PageUp else page
            if self._left_mouse_selecting:
                self._extend_selection_viewport(delta)
            else:
                self._change_shared_viewport(delta)
            event.accept()
            return
        if (
            self._large_binary_mode
            and key in {Qt.Key_Up, Qt.Key_Down}
            and event.modifiers() == Qt.NoModifier
        ):
            block = self.textCursor().blockNumber()
            last_block = max(0, self.document().blockCount() - 1)
            if (key == Qt.Key_Up and block == 0) or (key == Qt.Key_Down and block == last_block):
                delta = -ROW_BYTES if key == Qt.Key_Up else ROW_BYTES
                self._change_shared_viewport(delta)
                event.accept()
                return
        super().keyPressEvent(event)
        self._refresh_completions()
        self._normalize_instruction_after_comment_start(event.text())

    def _normalize_instruction_after_comment_start(self, text: str) -> None:
        if text in {";", "#"}:
            self._normalize_current_instruction_line()

    def _normalize_instruction_line_after_offset_change(self) -> None:
        block_number = self.textCursor().blockNumber()
        previous = self._last_instruction_cursor_block
        self._last_instruction_cursor_block = block_number
        if self._normalizing_instruction_line or previous is None or previous == block_number:
            return
        self._normalize_instruction_block(self.document().findBlockByNumber(previous))

    def _normalize_current_instruction_line(self) -> None:
        self._normalize_instruction_block(self.textCursor().block())

    def _normalize_instruction_block(self, block) -> None:
        if self._normalizing_instruction_line or not self._uppercase_instruction_cursor or not block.isValid():
            return
        text = block.text()
        normalized = normalize_instruction_text(text, True)
        if normalized == text:
            return
        current = self.textCursor()
        cursor = QTextCursor(block)
        self._normalizing_instruction_line = True
        try:
            cursor.joinPreviousEditBlock()
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            cursor.insertText(normalized)
            cursor.endEditBlock()
            self.setTextCursor(current)
        finally:
            self._normalizing_instruction_line = False
            self._last_instruction_cursor_block = self.textCursor().blockNumber()

    def normalize_granular_instruction_line(self) -> None:
        if not self._is_instruction_editor() or not self._uppercase_instruction_cursor:
            return
        cursor = self.textCursor()
        block = cursor.block()
        text = block.text()
        normalized = normalize_instruction_text(text, True)
        if normalized == text or len(normalized) != len(text):
            return
        position = cursor.position()
        normalizer = QTextCursor(block)
        self._normalizing_instruction_line = True
        try:
            normalizer.select(QTextCursor.SelectionType.LineUnderCursor)
            normalizer.insertText(normalized)
            set_cursor_position(cursor, position)
            self.setTextCursor(cursor)
        finally:
            self._normalizing_instruction_line = False
            self._last_instruction_cursor_block = self.textCursor().blockNumber()

    def _hex_text_event(self, event: QKeyEvent) -> QKeyEvent | None:
        text = event.text()
        if not self._hex_input_enabled or not text:
            return event
        if not any(_is_printable_text_input(char) for char in text):
            return event
        filtered = "".join(char for char in text if char in HEX_DIGITS)
        if not filtered:
            return None
        if self._uppercase_hex_input:
            filtered = filtered.upper()
        if filtered == text:
            return event
        return QKeyEvent(
            event.type(),
            event.key(),
            event.modifiers(),
            filtered,
            event.isAutoRepeat(),
            event.count(),
        )

    def mark_return_key_handled(self) -> None:
        self._return_key_handled = True

    def mark_protected_edit_key_handled(self) -> None:
        self._protected_edit_key_handled = True

    def wheelEvent(self, event) -> None:
        if self._shared_scrollbar is None:
            super().wheelEvent(event)
            return
        delta = event.pixelDelta().y()
        if delta == 0:
            delta = (event.angleDelta().y() // BINARY_WORKBENCH_LAYOUT.WHEEL_SCROLL_DIVISOR) * ROW_BYTES
        movement = -delta
        if self._left_mouse_selecting or bool(event.buttons() & Qt.LeftButton):
            self._extend_selection_viewport(movement, event.position().toPoint())
        else:
            self._change_shared_viewport(movement)
        event.accept()

    def _change_shared_viewport(self, delta: int) -> None:
        cursor_state = self._cursor_viewport_state() if self._large_binary_mode else None
        if cursor_state is None:
            self.viewportChangeAboutToStart.emit(self)
        previous = self._shared_scrollbar.value()
        self._shared_scrollbar.setValue(previous + delta)
        if self._shared_scrollbar.value() == previous:
            if cursor_state is None:
                self.viewportChangeFinished.emit(self)
            return
        if cursor_state is not None:
            self._restore_cursor_viewport_state(*cursor_state)
        self.viewportChangeFinished.emit(self)

    def _cursor_viewport_state(self) -> tuple[int, int] | None:
        cursor = self.textCursor()
        if cursor.hasSelection():
            return None
        return cursor.blockNumber(), cursor.positionInBlock()

    def _restore_cursor_viewport_state(self, block_number: int, position: int) -> None:
        block_number = min(max(0, block_number), max(0, self.document().blockCount() - 1))
        block = self.document().findBlockByNumber(block_number)
        cursor = self.textCursor()
        set_cursor_position(cursor, block.position() + min(position, len(block.text())))
        scrollbar = self.verticalScrollBar()
        scroll_value = scrollbar.value()
        editor_blocker = QSignalBlocker(self)
        scrollbar_blocker = QSignalBlocker(scrollbar)
        self.setTextCursor(cursor)
        scrollbar.setValue(scroll_value)
        del scrollbar_blocker
        del editor_blocker

    def leaveEvent(self, event) -> None:
        self.viewport().setCursor(Qt.IBeamCursor)
        if not (self.textCursor().hasSelection() and self.hasFocus()):
            self._stop_selection_scroll()
        super().leaveEvent(event)

    def eventFilter(self, watched, event) -> bool:
        completer = getattr(self, "_completer", None)
        if completer is None:
            return super().eventFilter(watched, event)
        popup = completer.popup()
        if (
            watched is self
            and popup.isVisible()
            and event.type() == QEvent.Type.KeyPress
            and event.key() in _COMPLETION_NAVIGATION_KEYS
        ):
            popup.hide()
            self.keyPressEvent(event)
            event.accept()
            return True
        if (watched is popup or watched is popup.viewport()) and event.type() == QEvent.Type.KeyPress:
            if event.key() in {Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab}:
                self._accept_current_completion()
                event.accept()
                return True
            if event.key() == Qt.Key_Escape:
                popup.hide()
                event.accept()
                return True
        return super().eventFilter(watched, event)


def _alt_shortcut_event(event: QKeyEvent) -> bool:
    return bool(event.modifiers() & Qt.AltModifier) and not bool(
        event.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier | Qt.MetaModifier)
    )


def _is_printable_text_input(char: str) -> bool:
    return char.isprintable() and char not in {"\t", "\r", "\n"}
