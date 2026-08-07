from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import (
    QEvent,
    QPoint,
    QSignalBlocker,
    QStringListModel,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QKeyEvent, QKeySequence, QPainter, QTextCursor
from PySide6.QtWidgets import QCompleter, QFrame, QListView, QPlainTextEdit, QScrollBar, QWidget

from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES
from src.modules.constants import HEX_DIGITS
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TIMING,
)
from src.presentation.ui.components.binary_workbench.editor.editor_completion import EditorCompletionMixin
from src.core.debugger.directives.constants import DEBUGGER_DIRECTIVE_NAMES
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
    byte_cursor_position,
    format_byte_groups,
    normalize_instruction_text,
)
from src.presentation.ui.components.binary_workbench.editor.cursor_guard import (
    capture_logical_cursor,
    restore_logical_cursor,
    set_cursor_position,
)
from src.presentation.ui.helpers.load_qss import STYLESHEET


_COMPLETION_NAVIGATION_KEYS = {
    Qt.Key_Up,
    Qt.Key_Down,
    Qt.Key_Left,
    Qt.Key_Right,
}


@dataclass(frozen=True)
class StructuralHistoryCommand:
    """Describe a native history command that removed source rows."""

    undo_steps_before: int
    undo_steps_after: int
    block: int
    position: int
    requires_byte_shift: bool


@dataclass(frozen=True)
class DerivedProjectionHistoryCommand:
    """Identify one automatic UI projection inside Qt's native history."""

    undo_steps_before: int
    undo_steps_after: int


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
    editAboutToStart = Signal(object, object)
    editFinished = Signal(object)
    protectedEditKeyPressed = Signal(object, object)
    navigationWarningRequested = Signal(str)
    labelFoldToggled = Signal(str)
    directiveFoldToggled = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self._shared_scrollbar: QScrollBar | None = None
        self._completion_model = QStringListModel(self)
        self._completion_items: dict[str, list[str]] = {
            "label": [],
            "variable": [],
            "equate": [],
            "command": [],
            "directive": list(DEBUGGER_DIRECTIVE_NAMES),
        }
        self._symbol_tooltips: dict[str, str] = {}
        self._lazy_symbol_maps: tuple[dict[str, str], dict[str, str]] = ({}, {})
        self._pressed_symbol_token = ""
        self._label_offsets: dict[str, tuple[str, int]] = {}
        self._label_target_resolver = None
        self._jump_label_symbols: set[str] = set()
        self._jump_codec = None
        self._jump_symbols: dict[str, str] = {}
        self._jump_symbol_kinds: dict[str, str] = {}
        self._hex_input_enabled = False
        self._uppercase_hex_input = False
        self._hex_group_size = 1
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
        self._edit_preflight_handled = False
        self._history_action_in_progress = False
        self._crossing_derived_projection_history = False
        self._structural_history_commands: dict[int, StructuralHistoryCommand] = {}
        self._derived_projection_commands: dict[int, DerivedProjectionHistoryCommand] = {}
        self._derived_projection_depth = 0
        self._derived_projection_cursor: QTextCursor | None = None
        self._derived_projection_undo_steps = 0
        self._history_high_watermark = self.document().availableUndoSteps()
        self.document().undoCommandAdded.connect(self._on_undo_command_added)
        self._selection_timer = QTimer(self)
        self._selection_timer.timeout.connect(self._step_selection_scroll)
        self._completion_navigation_timer = QTimer(self)
        self._completion_navigation_timer.setSingleShot(True)
        self._completion_navigation_timer.setInterval(
            BINARY_WORKBENCH_TIMING.EDITOR_COMPLETION_NAVIGATION_DEBOUNCE_MS
        )
        self._completion_navigation_timer.timeout.connect(self._refresh_completions)
        self._symbol_completion_timer = QTimer(self)
        self._symbol_completion_timer.setSingleShot(True)
        self._symbol_completion_timer.timeout.connect(self._refresh_completions)
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

    def set_hex_input_mode(self, enabled: bool, uppercase: bool, group_size: int = 1) -> None:
        self._hex_input_enabled = enabled
        self._uppercase_hex_input = uppercase
        self._hex_group_size = max(1, group_size)

    def set_uppercase_hex_input(self, enabled: bool) -> None:
        self.set_hex_input_mode(True, enabled, self._hex_group_size)

    def set_content_alignment(self, alignment: Qt.AlignmentFlag) -> None:
        """Set a persistent paragraph alignment without rewriting the document."""

        option = self.document().defaultTextOption()
        option.setAlignment(alignment)
        self.document().setDefaultTextOption(option)
        self.viewport().update()

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
        self.editFinished.emit(self)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        document_edit = _may_edit_document(event)
        deleting = event.key() in {Qt.Key_Backspace, Qt.Key_Delete}
        if event.key() in _COMPLETION_NAVIGATION_KEYS:
            self._debounce_completions_after_navigation()
        if document_edit:
            self._edit_preflight_handled = False
            self.clear_bytes_row_removal_authorization()
            self.editAboutToStart.emit(self, event)
            if self._edit_preflight_handled:
                event.accept()
                return
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
            self._run_history_action(self.undo, undo=True)
            event.accept()
            return
        if event.matches(QKeySequence.Redo) or (
            event.key() == Qt.Key_Z
            and bool(event.modifiers() & Qt.ControlModifier)
            and bool(event.modifiers() & Qt.ShiftModifier)
        ):
            self._run_history_action(self.redo, undo=False)
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
            if document_edit:
                self._schedule_completions_after_edit(deleting=deleting)
            self._normalize_instruction_after_comment_start(event.text())
            event.accept()
            return
        if event.key() == Qt.Key_Tab:
            self.insertPlainText(" " * BINARY_WORKBENCH_LAYOUT.EDITOR_TAB_SPACES)
            event.accept()
            return
        if self._shared_scrollbar is None:
            super().keyPressEvent(event)
            if document_edit:
                self._schedule_completions_after_edit(deleting=deleting)
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
        if document_edit:
            self._schedule_completions_after_edit(deleting=deleting)
        self._normalize_instruction_after_comment_start(event.text())

    def _run_history_action(self, action, *, undo: bool) -> None:
        """Run undo/redo and retain Qt's caret at the affected edit location."""

        previous_cursor = capture_logical_cursor(self)
        previous_visible_blocks = self._visible_block_range()
        previous_local_scroll = self.verticalScrollBar().value()
        previous_shared_scroll = (
            self._shared_scrollbar.value()
            if self._shared_scrollbar is not None
            else None
        )
        previous_text = self.toPlainText()
        previous_steps = self._available_history_steps(undo)
        previous_undo_steps = self.document().availableUndoSteps()
        self._history_action_in_progress = True
        try:
            if not self._skip_derived_projection_history(action, undo=undo):
                return
            action()
            self._skip_bytes_no_op_history(
                action,
                undo=undo,
                previous_text=previous_text,
                previous_steps=previous_steps,
            )
        finally:
            self._history_action_in_progress = False
        action_performed = (
            self.toPlainText() != previous_text
            or self._available_history_steps(undo) != previous_steps
        )
        structural_target = self._resolved_structural_undo_cursor(
            undo,
            previous_undo_steps,
        )
        if action_performed and structural_target is not None:
            self._restore_cursor_viewport_state(*structural_target)
        cursor_state = (
            capture_logical_cursor(self) if action_performed else previous_cursor
        )
        target_block = (
            structural_target[0]
            if structural_target is not None
            else cursor_state.position_block
        )
        preserve_visible_viewport = (
            action_performed
            and previous_visible_blocks[0]
            <= target_block
            <= previous_visible_blocks[1]
        )
        local_scroll = (
            previous_local_scroll
            if preserve_visible_viewport
            else self.verticalScrollBar().value()
            if action_performed
            else previous_local_scroll
        )
        shared_scroll = (
            previous_shared_scroll
            if preserve_visible_viewport
            else self._shared_scrollbar.value()
            if action_performed and self._shared_scrollbar is not None
            else previous_shared_scroll
        )
        self._restore_history_interaction(cursor_state, local_scroll, shared_scroll)
        revision = self.document().revision()
        cursor_position = self.textCursor().position()
        QTimer.singleShot(
            0,
            lambda: self._restore_history_interaction_if_unchanged(
                cursor_state,
                local_scroll,
                shared_scroll,
                revision,
                cursor_position,
            ),
        )

    def begin_derived_projection(self) -> None:
        """Group automatic document updates into one non-user history entry."""

        if self._derived_projection_depth == 0:
            self._derived_projection_undo_steps = self.document().availableUndoSteps()
            self._derived_projection_cursor = QTextCursor(self.document())
            self._derived_projection_cursor.beginEditBlock()
        self._derived_projection_depth += 1

    def end_derived_projection(self) -> None:
        """Mark the completed projection so Undo/Redo can ignore it."""

        if self._derived_projection_depth <= 0:
            return
        self._derived_projection_depth -= 1
        if self._derived_projection_depth:
            return
        cursor = self._derived_projection_cursor
        self._derived_projection_cursor = None
        if cursor is not None:
            cursor.endEditBlock()
        before = self._derived_projection_undo_steps
        after = self.document().availableUndoSteps()
        if after > before:
            self._derived_projection_commands[after] = DerivedProjectionHistoryCommand(
                before,
                after,
            )
            self._history_high_watermark = max(self._history_high_watermark, after)

    def reset_native_history_metadata(self) -> None:
        """Forget metadata after an authoritative full-document replacement."""

        self._structural_history_commands.clear()
        self._derived_projection_commands.clear()
        self._derived_projection_depth = 0
        self._derived_projection_cursor = None
        self._derived_projection_undo_steps = 0
        self._history_high_watermark = self.document().availableUndoSteps()

    def _skip_derived_projection_history(self, action, *, undo: bool) -> bool:
        """Cross automatic commands only when a real user command exists beyond them."""

        while command := self._next_derived_projection_command(undo):
            if not self._user_history_exists_beyond(command, undo=undo):
                return False
            self._crossing_derived_projection_history = True
            try:
                action()
            finally:
                self._crossing_derived_projection_history = False
        return (
            self.document().isUndoAvailable()
            if undo
            else self.document().isRedoAvailable()
        )

    def crossing_derived_projection_history(self) -> bool:
        """Report an internal Undo crossing that must not update source state."""

        return self._crossing_derived_projection_history

    def _next_derived_projection_command(
        self,
        undo: bool,
    ) -> DerivedProjectionHistoryCommand | None:
        current = self.document().availableUndoSteps()
        if undo:
            return self._derived_projection_commands.get(current)
        return next(
            (
                command
                for command in self._derived_projection_commands.values()
                if command.undo_steps_before == current
            ),
            None,
        )

    def _user_history_exists_beyond(
        self,
        command: DerivedProjectionHistoryCommand,
        *,
        undo: bool,
    ) -> bool:
        """Inspect history metadata without applying a visual projection command."""

        if undo:
            position = command.undo_steps_before
            while position > 0:
                projected = self._derived_projection_commands.get(position)
                if projected is None:
                    return True
                position = projected.undo_steps_before
            return False
        position = command.undo_steps_after
        end = (
            self.document().availableUndoSteps()
            + self.document().availableRedoSteps()
        )
        while position < end:
            projected = next(
                (
                    item
                    for item in self._derived_projection_commands.values()
                    if item.undo_steps_before == position
                ),
                None,
            )
            if projected is None:
                return True
            position = projected.undo_steps_after
        return False

    def remember_structural_undo_cursor(
        self,
        block: int,
        position: int,
        *,
        requires_byte_shift: bool = True,
        undo_steps_before: int | None = None,
    ) -> None:
        """Record one row command without merging it with character edits."""

        steps = self.document().availableUndoSteps()
        self._structural_history_commands[steps] = StructuralHistoryCommand(
            max(0, steps - 1) if undo_steps_before is None else undo_steps_before,
            steps,
            block,
            position,
            requires_byte_shift,
        )
        self._history_high_watermark = max(self._history_high_watermark, steps)

    def history_action_requires_byte_shift(self, undo: bool) -> bool:
        """Return whether the next history command removes or restores rows."""

        command = self.next_structural_history_command(undo)
        return bool(command and command.requires_byte_shift)

    def next_structural_history_command(
        self,
        undo: bool,
    ) -> StructuralHistoryCommand | None:
        """Return structural metadata for the next native Undo or Redo."""

        undo_steps = self.document().availableUndoSteps()
        if undo:
            return self._structural_history_commands.get(undo_steps)
        return next(
            (
                command
                for command in self._structural_history_commands.values()
                if command.undo_steps_before == undo_steps
            ),
            None,
        )

    def _on_undo_command_added(self) -> None:
        """Discard structural metadata from a native history branch replacement."""

        current = self.document().availableUndoSteps()
        if self._derived_projection_depth == 0:
            self._derived_projection_commands = {
                key: value
                for key, value in self._derived_projection_commands.items()
                if value.undo_steps_after < current
            }
        if current <= self._history_high_watermark:
            self._structural_history_commands = {
                key: value
                for key, value in self._structural_history_commands.items()
                if key < current
            }
        self._history_high_watermark = max(current, self._history_high_watermark)

    def _resolved_structural_undo_cursor(
        self,
        undo: bool,
        previous_undo_steps: int,
    ) -> tuple[int, int] | None:
        """Return the structural command crossed by the completed history action."""

        current_steps = self.document().availableUndoSteps()
        for command in self._structural_history_commands.values():
            crossed = (
                previous_undo_steps >= command.undo_steps_after
                and current_steps <= command.undo_steps_before
                if undo
                else previous_undo_steps <= command.undo_steps_before
                and current_steps >= command.undo_steps_after
            )
            if crossed:
                return command.block, command.position
        return None

    def _restore_history_interaction_if_unchanged(
        self,
        cursor_state,
        local_scroll: int,
        shared_scroll: int | None,
        revision: int,
        cursor_position: int,
    ) -> None:
        """Do not let a queued Undo restoration overwrite a newer interaction."""

        if (
            self.document().revision() != revision
            or self.textCursor().position() != cursor_position
        ):
            return
        self._restore_history_interaction(cursor_state, local_scroll, shared_scroll)

    def _skip_bytes_no_op_history(
        self,
        action,
        *,
        undo: bool,
        previous_text: str,
        previous_steps: int,
    ) -> None:
        """Skip visual-only history entries before the next Bytes text change."""

        if not self._hex_input_enabled:
            return
        for _unused in range(BINARY_WORKBENCH_TIMING.EDITOR_NO_OP_HISTORY_LIMIT):
            current_steps = self._available_history_steps(undo)
            if self.toPlainText() != previous_text or current_steps >= previous_steps:
                return
            available = (
                self.document().isUndoAvailable()
                if undo
                else self.document().isRedoAvailable()
            )
            if not available:
                return
            if self.history_action_requires_byte_shift(undo):
                return
            previous_steps = current_steps
            action()

    def _visible_block_range(self) -> tuple[int, int]:
        """Return the logical rows currently visible without moving the caret."""

        first = self.cursorForPosition(QPoint(0, 0)).blockNumber()
        bottom = max(0, self.viewport().height() - 1)
        last = self.cursorForPosition(QPoint(0, bottom)).blockNumber()
        return min(first, last), max(first, last)

    def _available_history_steps(self, undo: bool) -> int:
        """Return the current number of commands in one history direction."""

        document = self.document()
        return document.availableUndoSteps() if undo else document.availableRedoSteps()

    def _restore_history_interaction(
        self,
        cursor_state,
        local_scroll: int,
        shared_scroll: int | None,
    ) -> None:
        """Restore row-relative cursor and scroll state after queued projections."""

        editor_blocker = QSignalBlocker(self)
        local_bar = self.verticalScrollBar()
        local_blocker = QSignalBlocker(local_bar)
        shared_blocker = (
            QSignalBlocker(self._shared_scrollbar)
            if self._shared_scrollbar is not None
            else None
        )
        restore_logical_cursor(self, cursor_state)
        # The column layout reparents this editor into its shell.  The shared
        # scrollbar, however, remains owned by BinaryWorkbenchGrid and is the
        # stable route back to the component that synchronizes every column.
        parent = (
            self._shared_scrollbar.parentWidget()
            if self._shared_scrollbar is not None
            else self.parentWidget()
        )
        synchronize_static = (
            getattr(parent, "_scroll_static_document", None)
            if parent is not None and not getattr(parent, "_virtual", False)
            else None
        )
        if synchronize_static is None:
            local_bar.setValue(min(local_scroll, local_bar.maximum()))
        if self._shared_scrollbar is not None and shared_scroll is not None:
            self._shared_scrollbar.setValue(
                min(shared_scroll, self._shared_scrollbar.maximum())
            )
        del shared_blocker
        del local_blocker
        del editor_blocker
        if synchronize_static is not None and shared_scroll is not None:
            synchronize_static(
                min(shared_scroll, self._shared_scrollbar.maximum())
            )

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
        current_position = current.position()
        current_anchor = current.anchor()
        cursor = QTextCursor(block)
        self._normalizing_instruction_line = True
        try:
            cursor.joinPreviousEditBlock()
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            cursor.insertText(normalized)
            cursor.endEditBlock()
            restored = QTextCursor(self.document())
            set_cursor_position(restored, current_anchor)
            set_cursor_position(restored, current_position, QTextCursor.KeepAnchor)
            self.setTextCursor(restored)
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

    def normalize_granular_bytes_line(self, cursor: QTextCursor) -> None:
        if not self._hex_input_enabled:
            return
        block = cursor.block()
        text = block.text()
        position_in_block = cursor.positionInBlock()
        raw_index = sum(char in HEX_DIGITS for char in text[:position_in_block])
        raw = "".join(char for char in text if char in HEX_DIGITS)[: ROW_BYTES * 2]
        normalized = format_byte_groups(raw, self._hex_group_size)
        group_width = self._hex_group_size * 2
        trailing_group_space = (
            0 < len(raw) < ROW_BYTES * 2
            and len(raw) % group_width == 0
        )
        if trailing_group_space:
            normalized = f"{normalized} "
        if normalized == text:
            return
        normalizer = QTextCursor(block)
        normalizer.select(QTextCursor.SelectionType.LineUnderCursor)
        normalizer.insertText(normalized)
        position = byte_cursor_position(normalized, raw_index)
        if trailing_group_space and raw_index == len(raw):
            position = len(normalized)
        set_cursor_position(cursor, block.position() + position)

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

    def mark_edit_preflight_handled(self) -> None:
        """Stop one mutating key event before it reaches the Qt document."""

        self._edit_preflight_handled = True

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


def _may_edit_document(event: QKeyEvent) -> bool:
    """Return whether a key event can mutate the editor document."""

    if event.key() in {
        Qt.Key_Return,
        Qt.Key_Enter,
        Qt.Key_Tab,
        Qt.Key_Backspace,
        Qt.Key_Delete,
    }:
        return True
    if (
        event.matches(QKeySequence.Cut)
        or event.matches(QKeySequence.Paste)
        or event.matches(QKeySequence.Undo)
        or event.matches(QKeySequence.Redo)
    ):
        return True
    if not event.text():
        return False
    return not bool(event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier))


def _alt_shortcut_event(event: QKeyEvent) -> bool:
    return bool(event.modifiers() & Qt.AltModifier) and not bool(
        event.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier | Qt.MetaModifier)
    )


def _is_printable_text_input(char: str) -> bool:
    return char.isprintable() and char not in {"\t", "\r", "\n"}
