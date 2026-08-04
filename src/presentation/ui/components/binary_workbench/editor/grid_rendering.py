from PySide6.QtCore import QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QPlainTextEdit

from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_BYTE_GROUP_OPTIONS,
    BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES,
)
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import (
    normalize_bytes_text,
    normalize_instruction_text,
)
from src.presentation.ui.components.binary_workbench.editor.cursor_guard import (
    set_cursor_position,
)
from src.core.binary_workbench.encoding_tables import decode_hex_bytes
from src.core.binary_workbench.row_structure import (
    first_valid_label_offset,
    valid_offset_end,
)


class GridRenderingMixin:
    def load_rows(
        self,
        columns: list[str],
        rows: list[BinaryWorkbenchRowDTO],
        group_bytes: int = 1,
        start_offset: int = 0,
        total_size: int = 0,
        virtual: bool = False,
        uppercase_bytes: bool = True,
        uppercase_instructions: bool = True,
        reference_offset_bases: dict[str, str] | None = None,
        jump_reference_offset: str = "",
    ) -> None:
        self._cancel_incremental_instruction_update()
        self._setup_refresh_window()
        self._reset_virtual_undo_cache()
        self._clear_virtual_selection()
        content_columns = {
            BINARY_WORKBENCH_TEXT.BYTES,
            BINARY_WORKBENCH_TEXT.DECODED_TEXT,
            BINARY_WORKBENCH_TEXT.INSTRUCTION,
            BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS,
        }
        offsets = [name for name in columns if name not in content_columns]
        self._configured_columns = list(columns)
        self._visible_offset_columns = offsets
        self._reference_offset_bases = {BINARY_WORKBENCH_TEXT.FILE: "0x00000000", **dict(reference_offset_bases or {})}
        self._jump_reference_offset = jump_reference_offset if jump_reference_offset in self._reference_offset_bases else ""
        self._sync_offset_columns(offsets)
        visible = set(columns)
        self.offsets_host.setVisible(bool(offsets))
        self.raw_shell.setVisible(BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS in visible)
        self._apply_bytes_visibility()
        self.decoded_shell.setVisible(BINARY_WORKBENCH_TEXT.DECODED_TEXT in visible)
        self.instructions_shell.setVisible(True)
        if self._last_editor_kind not in visible:
            self._last_editor_kind = BINARY_WORKBENCH_TEXT.INSTRUCTION
        self._group_bytes = (
            group_bytes
            if group_bytes in BINARY_WORKBENCH_BYTE_GROUP_OPTIONS
            else BINARY_WORKBENCH_BYTE_GROUP_OPTIONS[0]
        )
        self._uppercase_bytes = uppercase_bytes
        self._uppercase_instructions = uppercase_instructions
        self.bytes.set_hex_input_mode(True, self._uppercase_bytes, self._group_bytes)
        self.instructions.set_uppercase_instruction_hover(self._uppercase_instructions)
        self._virtual = virtual
        for editor in (*self._offset_editors.values(), self.raw_instructions, self.bytes, self.decoded_text, self.instructions):
            editor.set_large_binary_mode(virtual)
        self._total_size = total_size if virtual else len(rows) * ROW_BYTES
        self._all_rows = [] if virtual else list(rows)
        self._dirty_editor_kind = None
        self._visible_start_offset = start_offset
        self._last_visible_offset = start_offset
        self._refresh_jump_navigation()
        if virtual:
            self._configure_scrollbar()
            self.render_rows(rows, start_offset)
        else:
            self._rows = list(rows)
            self._visible_start_offset = 0
            self._last_visible_offset = 0
            self._render()
            self._configure_scrollbar()
        coordinator = getattr(self, "_consistency_coordinator", None)
        if coordinator is not None:
            coordinator.reset(list(self._rows))
        self._schedule_layout_refresh()

    def render_rows(self, rows: list[BinaryWorkbenchRowDTO], start_offset: int) -> None:
        if self._virtual:
            if (
                self._viewport_line_selection is None
                and self._virtual_selection_range is None
            ):
                self._capture_viewport_line_selection()
            self._capture_virtual_undo(self._visible_start_offset, start_offset)
            if self._viewport_line_selection is not None:
                self._virtual_selection_scrolling = True
        self._rows = list(rows)
        self._visible_start_offset = start_offset
        self._refresh_jump_navigation()
        self._render()
        self._restore_virtual_undo(start_offset)
        if self._viewport_line_selection is not None:
            self._restore_viewport_line_selection()
        elif self._virtual_selection_range is not None:
            self._select_visible_virtual_range(*self._virtual_selection_range)
        self._dirty_editor_kind = None

    def set_symbols(
        self,
        labels: dict[str, str],
        variables: dict[str, str],
        equates: dict[str, str],
        symbol_offsets: dict[str, list[str]] | None = None,
    ) -> None:
        symbols_changed = (
            labels != self._labels
            or variables != self._variables
            or equates != self._equates
        )
        self._labels = dict(labels)
        self._variables = dict(variables)
        self._equates = dict(equates)
        self._symbol_offsets = dict(symbol_offsets or self._symbol_offsets)
        self._instruction_highlighter.set_symbols(labels, variables, equates)
        self._raw_instruction_highlighter.set_symbols(labels, variables, equates)
        self.instructions.set_symbol_helpers(labels, variables, equates)
        self._refresh_jump_navigation()
        if symbols_changed and hasattr(self, "raw_instructions"):
            restore_raw_selection = self._virtual and (
                self.raw_instructions.textCursor().hasSelection()
                or (
                    self._viewport_line_selection is not None
                    and self._viewport_line_selection[0]
                    == BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS
                )
            )
            if self.raw_instructions.textCursor().hasSelection():
                self._capture_viewport_line_selection(self.raw_instructions)
            self._render_raw_instructions()
            if restore_raw_selection:
                self._restore_viewport_line_selection()

    def current_labels(self) -> dict[str, str]:
        """Return the in-memory label snapshot used by branch navigation."""

        return dict(self._labels)

    def label_navigation_target(self, label: str) -> int | None:
        """Resolve one clicked label against the grid's current rows."""

        target = first_valid_label_offset(self._rows, label)
        if target is None:
            value = next(
                (
                    offset
                    for name, offset in self._labels.items()
                    if name.lower() == label.lower()
                ),
                None,
            )
            try:
                target = int(value, 0) if value is not None else None
            except ValueError:
                return None
        if target is None or target < 0 or target % ROW_BYTES != 0:
            return None
        file_size = self.current_file_size()
        if target >= file_size:
            fallback_size = max(file_size, valid_offset_end(self._rows))
            if self._virtual and fallback_size != file_size:
                self.set_virtual_total_size(fallback_size)
                file_size = fallback_size
        return target if target < file_size else None

    def _refresh_jump_navigation(self) -> None:
        self._instruction_highlighter.set_jump_reference_offsets(
            self._reference_offset_bases,
            self._jump_reference_offset,
            self.current_file_size(),
        )
        self.instructions.set_jump_navigation(
            self._codec,
            self._labels,
            self._variables,
            self._equates,
            self._reference_offset_bases,
            self._visible_offset_columns,
            self._jump_reference_offset,
            self._visible_start_offset if self._virtual else 0,
            ROW_BYTES,
        )

    def visible_size(self) -> int:
        return self._visible_row_count() * ROW_BYTES

    def current_file_size(self) -> int:
        if self._virtual:
            return self._total_size
        return valid_offset_end(self._all_rows)

    def set_virtual_total_size(self, size: int) -> None:
        if not self._virtual or size == self._total_size:
            return
        self._total_size = max(0, size)
        self._configure_scrollbar()
        self._refresh_jump_navigation()

    def export_rows(self) -> list[BinaryWorkbenchRowDTO]:
        return list(self._all_rows if not self._virtual else self._rows)

    def set_visible_offset(self, offset: int) -> None:
        target = min(max(0, offset), self.scrollbar.maximum())
        if self.scrollbar.value() == target:
            self._on_scrollbar_changed(target)
            return
        self.scrollbar.setValue(target)

    def _render(self) -> None:
        self._resize_editors()
        self._set_editor_text(self.bytes, [self._display_bytes_text(row.bytes_text) for row in self._rows])
        self._render_decoded_text()
        self._set_editor_text(self.instructions, [self._display_instruction(row.instruction) for row in self._rows])
        self._instruction_highlighter.rehighlight()
        self._render_raw_instructions()
        self._render_offsets()
        self._refresh_label_folding()
        self._emit_selection_summary()

    def _render_decoded_text(self) -> None:
        """Rebuild decoded rows from the same row snapshot as every column."""

        self._set_editor_text(
            self.decoded_text,
            [
                decode_hex_bytes(row.bytes_text, self._decoded_text_values)
                for row in self._rows
            ],
        )

    def _render_offsets(self) -> None:
        for name, editor in self._offset_editors.items():
            self._set_editor_text(
                editor,
                [
                    self._display_offset(
                        editor,
                        self._folded_offset_text(index, name, row.offsets.get(name, "")),
                    )
                    for index, row in enumerate(self._rows)
                ],
            )
            editor._rebuild_dash_labels()

    def _display_offset(self, editor: QPlainTextEdit, text: str) -> str:
        return text

    def _on_scrollbar_changed(self, value: int) -> None:
        if self._updating:
            return
        if not self._virtual:
            self._scroll_static_document(value)
            self._warn_if_assembly_refresh_needed()
            return
        offset = self._aligned_scroll_offset(value)
        direction = 1 if offset >= self._last_visible_offset else -1
        self._last_visible_offset = offset
        self.visibleWindowRequested.emit(offset, self.visible_size(), direction)

    def _scroll_static_document(self, value: int) -> None:
        offset = self._aligned_scroll_offset(value)
        row_index = self._visible_block_position(offset // ROW_BYTES)
        self._visible_start_offset = offset
        self._last_visible_offset = offset
        editors = [*self._offset_editors.values(), self.raw_instructions, self.bytes, self.decoded_text, self.instructions]
        self._syncing_editor_scrollbars = True
        try:
            for editor in editors:
                editor.verticalScrollBar().setValue(row_index)
            self._align_static_editors(editors, row_index)
        finally:
            self._syncing_editor_scrollbars = False
        self._schedule_static_scroll_alignment()

    def _align_static_editors(self, editors: list, row_index: int) -> None:
        """Align first visible blocks after programmatic or cursor scrolling."""

        reference = next(
            (
                editor
                for editor in editors
                if editor is not self.instructions
                and self._scroll_editor_enabled(editor)
            ),
            self.instructions,
        )
        expected_block = reference.firstVisibleBlock().blockNumber()
        for editor in editors:
            if (
                self._scroll_editor_enabled(editor)
                and editor.firstVisibleBlock().blockNumber() != expected_block
            ):
                self._force_static_scroll_alignment(editor, row_index)

    def _schedule_static_scroll_alignment(self) -> None:
        """Queue one post-layout alignment without creating recurring timers."""

        if getattr(self, "_static_scroll_alignment_scheduled", False):
            return
        self._static_scroll_alignment_scheduled = True
        QTimer.singleShot(0, self._run_static_scroll_alignment)

    def _run_static_scroll_alignment(self) -> None:
        """Reconcile editors after Qt has completed cursor auto-scrolling."""

        self._static_scroll_alignment_scheduled = False
        if self._virtual:
            return
        editors = [
            *self._offset_editors.values(),
            self.raw_instructions,
            self.bytes,
            self.decoded_text,
            self.instructions,
        ]
        row_index = self._visible_block_position(self.scrollbar.value() // ROW_BYTES)
        self._syncing_editor_scrollbars = True
        try:
            self._align_static_editors(editors, row_index)
        finally:
            self._syncing_editor_scrollbars = False

    def _force_static_scroll_alignment(self, editor, row_index: int) -> None:
        """Reapply one static scroll position after cursor-driven auto-scroll."""

        scrollbar = editor.verticalScrollBar()
        neighbour = row_index - 1 if row_index > scrollbar.minimum() else row_index + 1
        if neighbour <= scrollbar.maximum() and neighbour != row_index:
            scrollbar.setValue(neighbour)
        scrollbar.setValue(row_index)

    def _set_editor_text(self, editor: QPlainTextEdit, lines: list[str]) -> None:
        text = "\n".join(lines)
        current_text = editor.toPlainText()
        if current_text == text:
            if self._virtual:
                editor.verticalScrollBar().setValue(0)
            self._remember_editor_text_signature(editor)
            return
        current_lines = current_text.split("\n")
        if len(current_lines) == len(lines):
            self._replace_changed_editor_lines(editor, current_lines, lines)
            return
        was_updating = self._updating
        self._updating = True
        scroll_value = editor.verticalScrollBar().value()
        try:
            editor.setPlainText(text)
            if self._virtual:
                editor.verticalScrollBar().setValue(0)
            else:
                editor.verticalScrollBar().setValue(min(scroll_value, editor.verticalScrollBar().maximum()))
            self._remember_editor_text_signature(editor)
        finally:
            self._updating = was_updating

    def _replace_changed_editor_lines(
        self,
        editor: QPlainTextEdit,
        current: list[str],
        updated: list[str],
    ) -> None:
        """Patch same-sized documents without rebuilding unaffected blocks."""

        was_updating = self._updating
        self._updating = True
        active = editor.textCursor()
        position, anchor = active.position(), active.anchor()
        scroll_value = editor.verticalScrollBar().value()
        try:
            for index, (before, after) in enumerate(zip(current, updated)):
                if before == after:
                    continue
                block = editor.document().findBlockByNumber(index)
                cursor = QTextCursor(block)
                cursor.select(QTextCursor.SelectionType.LineUnderCursor)
                cursor.insertText(after)
            restored = QTextCursor(editor.document())
            set_cursor_position(restored, anchor)
            set_cursor_position(restored, position, QTextCursor.KeepAnchor)
            editor.setTextCursor(restored)
            editor.verticalScrollBar().setValue(
                min(scroll_value, editor.verticalScrollBar().maximum())
            )
            self._remember_editor_text_signature(editor)
        finally:
            self._updating = was_updating

    def _set_editor_line(
        self,
        editor: QPlainTextEdit,
        index: int,
        text: str,
    ) -> None:
        """Replace one derived row without rebuilding the editor document."""

        block = editor.document().findBlockByNumber(index)
        if not block.isValid() or block.text() == text:
            return
        was_updating = self._updating
        self._updating = True
        active = editor.textCursor()
        position, anchor = active.position(), active.anchor()
        scroll_value = editor.verticalScrollBar().value()
        try:
            cursor = QTextCursor(block)
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            cursor.insertText(text)
            refresh_offset = getattr(editor, "refresh_offset_block", None)
            if refresh_offset is not None:
                refresh_offset(index)
            restored = QTextCursor(editor.document())
            set_cursor_position(restored, anchor)
            set_cursor_position(restored, position, QTextCursor.KeepAnchor)
            editor.setTextCursor(restored)
            editor.verticalScrollBar().setValue(scroll_value)
            self._remember_editor_text_signature(editor)
        finally:
            self._updating = was_updating

    def _remember_editor_text_signature(self, editor: QPlainTextEdit) -> None:
        self._editor_text_signatures[id(editor)] = self._editor_text_signature(editor)

    def _has_meaningful_editor_change(self, editor: QPlainTextEdit) -> bool:
        return self._editor_text_signature(editor) != self._editor_text_signatures.get(id(editor), "")

    def _editor_text_signature(self, editor: QPlainTextEdit) -> str:
        if editor is self.instructions:
            return editor.toPlainText()
        return "\n".join(
            "".join(line.split())
            for line in editor.toPlainText().split("\n")
        )

    def _display_bytes_text(self, text: str) -> str:
        return normalize_bytes_text(text, self._group_bytes, self._uppercase_bytes)

    def _display_instruction(self, text: str) -> str:
        return normalize_instruction_text(text, self._uppercase_instructions)
