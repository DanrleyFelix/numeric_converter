from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPlainTextEdit, QScrollBar, QSizePolicy, QVBoxLayout, QWidget

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_LAYOUT, BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.highlighters import BytesHighlighter, InstructionHighlighter
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES
from src.presentation.ui.components.binary_workbench.editor.workbench_editor import WorkbenchEditor
from src.presentation.ui.components.binary_workbench.editor.grid_offsets import (
    CenteredDashWorkbenchEditor,
    OffsetWorkbenchEditor,
)


class GridLayoutMixin:
    """Build fixed text columns; rows are QTextBlocks, not per-row widgets."""

    def _build_ui(self) -> None:
        self._responsive_bytes_hidden = False
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(BINARY_WORKBENCH_LAYOUT.EDITOR_SPACING)
        self.canvas = QFrame(self)
        self.canvas.setObjectName("binary-workbench-editor-canvas")
        self.canvas_layout = QHBoxLayout(self.canvas)
        self.canvas_layout.setContentsMargins(0, 0, 0, 0)
        self.canvas_layout.setSpacing(BINARY_WORKBENCH_LAYOUT.EDITOR_SPACING)
        self.offsets_host = QFrame(self.canvas)
        self.offsets_host.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.offsets_layout = QHBoxLayout(self.offsets_host)
        self.offsets_layout.setContentsMargins(0, 0, 0, 0)
        self.offsets_layout.setSpacing(BINARY_WORKBENCH_LAYOUT.EDITOR_SPACING)
        self.scrollbar = QScrollBar(Qt.Vertical, self)
        self.scrollbar.setObjectName("binary-workbench-editor-scrollbar")
        self.scrollbar.valueChanged.connect(self._on_scrollbar_changed)
        self.raw_shell, self.raw_instructions = self._panel(BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS, "binary-workbench-raw-instructions-panel", True, BINARY_WORKBENCH_LAYOUT.EDITOR_RAW_INSTRUCTION_WIDTH, CenteredDashWorkbenchEditor)
        self.bytes_shell, self.bytes = self._panel(BINARY_WORKBENCH_TEXT.BYTES, "binary-workbench-bytes-panel", False, BINARY_WORKBENCH_LAYOUT.EDITOR_BYTES_WIDTH, CenteredDashWorkbenchEditor)
        self.bytes.set_content_alignment(Qt.AlignCenter)
        self.decoded_shell, self.decoded_text = self._panel(BINARY_WORKBENCH_TEXT.DECODED_TEXT, "binary-workbench-decoded-text-panel", True, BINARY_WORKBENCH_LAYOUT.EDITOR_DECODED_TEXT_WIDTH, CenteredDashWorkbenchEditor)
        self.instructions_shell, self.instructions = self._panel(BINARY_WORKBENCH_TEXT.INSTRUCTION, "binary-workbench-instructions-panel", False)
        self._bytes_highlighter = BytesHighlighter(
            self.bytes.document(),
            double_spacing=True,
        )
        self._raw_instruction_highlighter = InstructionHighlighter(
            self.raw_instructions.document(),
            semantic_validation=False,
        )
        self._raw_instruction_highlighter.set_navigation_background_enabled(False)
        self._instruction_highlighter = InstructionHighlighter(self.instructions.document())
        self._connect_editors()
        self.canvas_layout.addWidget(self.offsets_host, 0)
        self.canvas_layout.addWidget(self.raw_shell, 0)
        self.canvas_layout.addWidget(self.bytes_shell, 0)
        self.canvas_layout.addWidget(self.decoded_shell, 0)
        self.canvas_layout.addWidget(self.instructions_shell, 1)
        layout.addWidget(self.canvas, 1)
        layout.addWidget(self.scrollbar, 0)

    def _connect_editors(self) -> None:
        self.bytes.textChanged.connect(self._on_bytes_changed)
        self.instructions.textChanged.connect(self._on_instructions_changed)
        self.instructions.set_immediate_symbol_menu_enabled(True)
        self.instructions.set_label_target_resolver(self.label_navigation_target)
        self.instructions.immediateSymbolRequested.connect(self.immediateSymbolRequested)
        self.instructions.symbolEditRequested.connect(self.symbolEditRequested.emit)
        self.instructions.addCommandRequested.connect(self._add_custom_command_from_selection)
        self.instructions.labelActivated.connect(self.labelActivated)
        self.instructions.jumpNavigationActivated.connect(self.jumpNavigationActivated)
        self.instructions.labelFoldToggled.connect(self.toggle_label_fold)
        self.instructions.directiveFoldToggled.connect(self.toggle_directive_fold)
        self.instructions.labelOpenTabRequested.connect(self.labelOpenTabRequested)
        self.instructions.navigationWarningRequested.connect(self.navigationWarningRequested)
        self.raw_instructions.focused.connect(lambda: self._set_last_editor(BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS))
        self.bytes.focused.connect(lambda: self._set_last_editor(BINARY_WORKBENCH_TEXT.BYTES))
        self.instructions.focused.connect(lambda: self._set_last_editor(BINARY_WORKBENCH_TEXT.INSTRUCTION))
        self.raw_instructions.cursorPositionChanged.connect(self._emit_selection_summary)
        self.bytes.cursorPositionChanged.connect(self._emit_selection_summary)
        self.instructions.cursorPositionChanged.connect(self._emit_selection_summary)
        for editor in (
            self.raw_instructions,
            self.bytes,
            self.decoded_text,
            self.instructions,
        ):
            editor.selectionChanged.connect(
                lambda source=editor: self._queue_selection_projection(source)
            )
        for editor in (self.raw_instructions, self.bytes, self.instructions):
            editor.copyRequested.connect(self._copy_editor_selection)
            editor.selectionStarted.connect(self._clear_virtual_selection)
            editor.selectionAutoScrollAboutToStep.connect(self._capture_virtual_selection_anchor)
            editor.selectionAutoScrolled.connect(self._restore_virtual_selection)
            editor.viewportChangeAboutToStart.connect(self._capture_virtual_viewport_selection)
            editor.viewportChangeFinished.connect(self._finish_virtual_viewport_change)
            editor.verticalScrollBar().valueChanged.connect(
                lambda value, source=editor: self._on_editor_scrollbar_changed(
                    source,
                    value,
                )
            )
            editor.returnKeyPressed.connect(self._handle_editor_return_key)
            editor.editAboutToStart.connect(self._prepare_editor_edit)
            editor.editFinished.connect(self._finish_editor_edit)
            editor.protectedEditKeyPressed.connect(self._handle_editor_protected_edit_key)
        self.bytes.cursorPositionChanged.connect(self._finish_staged_bytes_after_navigation)
        self.decoded_text.copyRequested.connect(lambda source: source.copy())
        self.decoded_text.verticalScrollBar().valueChanged.connect(
            lambda value: self._on_editor_scrollbar_changed(
                self.decoded_text,
                value,
            )
        )

    def _panel(
        self,
        label_text: str,
        object_name: str,
        read_only: bool,
        width: int | None = None,
        editor_type: type[WorkbenchEditor] = WorkbenchEditor,
    ) -> tuple[QFrame, WorkbenchEditor]:
        shell = QFrame(self)
        shell.setObjectName("binary-workbench-column-shell")
        shell.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(BINARY_WORKBENCH_LAYOUT.PANEL_LABEL_SPACING)
        label = QLabel(label_text, shell)
        label.setObjectName("binary-workbench-column-label")
        label.setContentsMargins(BINARY_WORKBENCH_LAYOUT.PANEL_LABEL_LEFT_MARGIN, 0, 0, 0)
        editor = self._editor(object_name, read_only, width, editor_type)
        if width is not None:
            shell.setFixedWidth(width)
            shell.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        layout.addWidget(label, 0)
        layout.addWidget(editor, 1)
        return shell, editor

    def _editor(
        self,
        object_name: str,
        read_only: bool,
        width: int | None = None,
        editor_type: type[WorkbenchEditor] = WorkbenchEditor,
    ) -> WorkbenchEditor:
        editor = editor_type(self)
        editor.setObjectName(object_name)
        editor.setReadOnly(read_only)
        editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        editor.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        editor.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        editor.document().setDocumentMargin(BINARY_WORKBENCH_LAYOUT.EDITOR_DOCUMENT_MARGIN)
        editor.set_shared_scrollbar(self.scrollbar)
        editor.selectAllRequested.connect(
            editor.selectAll if read_only and object_name != "binary-workbench-raw-instructions-panel" else self.selectAllRequested.emit
        )
        if width is not None:
            editor.setFixedWidth(width)
        return editor

    def set_responsive_bytes_hidden(self, hidden: bool) -> None:
        """Hide Bytes responsively without changing the user's column preference."""

        self._responsive_bytes_hidden = hidden
        self._apply_bytes_visibility()

    def _apply_bytes_visibility(self) -> None:
        """Apply the configured Bytes column visibility and window-width override."""

        configured = BINARY_WORKBENCH_TEXT.BYTES in getattr(self, "_configured_columns", [])
        self.bytes_shell.setVisible(configured and not self._responsive_bytes_hidden)

    def _prepare_editor_edit(self, editor, event) -> None:
        """Expand source folds and reject unsafe direct Bytes mutations."""

        undo = event.matches(QKeySequence.Undo)
        redo = event.matches(QKeySequence.Redo) or (
            event.key() == Qt.Key_Z
            and bool(event.modifiers() & Qt.ControlModifier)
            and bool(event.modifiers() & Qt.ShiftModifier)
        )
        if (
            (undo or redo)
            and editor.history_action_requires_byte_shift(undo)
            and not self._edit_rules.allow_byte_shift
            and not self._free_offset_window()
        ):
            self.commandWarningRequested.emit(
                BINARY_WORKBENCH_TEXT.STATUS_HISTORY_BYTE_SHIFTING_DISABLED
            )
            editor.mark_edit_preflight_handled()
            return

        if editor is self.bytes:
            structural_history = (
                editor.next_structural_history_command(undo)
                if undo or redo
                else None
            )
            first, last = self._byte_edit_event_rows(editor.textCursor())
            # A multicursor edit mutates several blocks inside one Qt edit block.
            # Treating the visible/current cursor as a single-row hint commits only
            # that row and leaves the other Bytes changes stale in Assembly.
            self._bytes_edit_block_hint = (
                first
                if first == last and not editor.has_multicursor_ranges()
                else None
            )
            self._bytes_edit_alignment_hint = (
                structural_history.block
                if structural_history is not None
                else self._byte_edit_alignment_boundary(editor, event, first)
            )
            if not self._bytes_edit_event_allowed(editor, event):
                self._bytes_edit_block_hint = None
                self._bytes_edit_alignment_hint = None
                editor.mark_edit_preflight_handled()
                return

        if editor is self.instructions:
            coordinator = getattr(self, "_consistency_coordinator", None)
            if coordinator is not None and coordinator.enabled():
                coordinator.begin_user_event("key")
                ranges = list(getattr(editor, "_occurrence_ranges", ()))
                if not ranges:
                    cursor = editor.textCursor()
                    ranges = [(cursor.selectionStart(), cursor.selectionEnd())]
                coordinator.register_source_edit_ranges(ranges)
            move_to_end = event.key() in {Qt.Key_Return, Qt.Key_Enter}
            self.expand_collapsed_label_at_cursor(editor, move_to_end)

    def _finish_editor_edit(self, editor) -> None:
        """Discard a partial Bytes transaction when its editor loses focus."""

        if editor is self.bytes and self._bytes_staged_incomplete:
            self._restore_editor_after_rejected_change(True)

    def _finish_staged_bytes_after_navigation(self) -> None:
        """Discard a partial Bytes transaction before editing another row.

        Native Undo temporarily moves Qt's caret while restoring a command. It
        is not user navigation and must never discard the remaining history.
        """

        if not self._bytes_staged_incomplete:
            return
        if bool(getattr(self.bytes, "_history_action_in_progress", False)):
            return
        if self.bytes.textCursor().blockNumber() != self._bytes_staged_block:
            self._restore_editor_after_rejected_change(True)

    def _configure_scrollbar(self) -> None:
        was_updating = self._updating
        self._updating = True
        try:
            maximum = max(0, self._scrollable_total_size() - self.visible_size())
            target = min(max(0, self._aligned_scroll_offset(self._visible_start_offset)), maximum)
            self._visible_start_offset = target
            self.scrollbar.setRange(0, maximum)
            self._ensure_static_editor_scroll_range(maximum)
            self.scrollbar.setSingleStep(ROW_BYTES)
            self.scrollbar.setPageStep(max(ROW_BYTES, self.visible_size()))
            self.scrollbar.setValue(target)
            if not self._virtual:
                self._scroll_static_document(target)
        finally:
            self._updating = was_updating

    def _on_editor_scrollbar_changed(self, editor, value: int) -> None:
        if (
            self._virtual
            or self._updating
            or self._syncing_editor_scrollbars
            or not self._scroll_editor_enabled(editor)
        ):
            return
        self.scrollbar.setValue(value * ROW_BYTES)

    def _scroll_editor_enabled(self, editor) -> bool:
        """Return whether an editor belongs to a currently enabled column."""

        if editor in self._offset_editors.values():
            return not self.offsets_host.isHidden()
        shells = {
            self.raw_instructions: self.raw_shell,
            self.bytes: self.bytes_shell,
            self.decoded_text: self.decoded_shell,
            self.instructions: self.instructions_shell,
        }
        return not shells[editor].isHidden()
