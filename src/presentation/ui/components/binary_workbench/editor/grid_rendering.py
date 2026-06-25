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
from src.core.binary_workbench.encoding_tables import decode_hex_bytes


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
    ) -> None:
        content_columns = {
            BINARY_WORKBENCH_TEXT.BYTES,
            BINARY_WORKBENCH_TEXT.DECODED_TEXT,
            BINARY_WORKBENCH_TEXT.INSTRUCTION,
            BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS,
        }
        offsets = [name for name in columns if name not in content_columns]
        self._sync_offset_columns(offsets)
        visible = set(columns)
        self.offsets_host.setVisible(bool(offsets))
        self.raw_shell.setVisible(BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS in visible)
        self.bytes_shell.setVisible(BINARY_WORKBENCH_TEXT.BYTES in visible)
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
        self._virtual = virtual
        for editor in (*self._offset_editors.values(), self.raw_instructions, self.bytes, self.decoded_text, self.instructions):
            editor.set_large_binary_mode(virtual)
        self._total_size = total_size if virtual else len(rows) * ROW_BYTES
        self._all_rows = [] if virtual else list(rows)
        self._dirty_editor_kind = None
        self._visible_start_offset = start_offset
        self._last_visible_offset = start_offset
        if virtual:
            self._configure_scrollbar()
            self.render_rows(rows, start_offset)
        else:
            self._rows = list(rows)
            self._visible_start_offset = 0
            self._last_visible_offset = 0
            self._render()
            self._configure_scrollbar()
        self._schedule_layout_refresh()

    def render_rows(self, rows: list[BinaryWorkbenchRowDTO], start_offset: int) -> None:
        self._rows = list(rows)
        self._visible_start_offset = start_offset
        self._render()
        if self._virtual_selection_range is not None:
            self._select_visible_virtual_range(*self._virtual_selection_range)
        self._dirty_editor_kind = None

    def set_symbols(
        self,
        labels: dict[str, str],
        variables: dict[str, str],
        equates: dict[str, str],
        symbol_offsets: dict[str, list[str]] | None = None,
    ) -> None:
        self._labels = dict(labels)
        self._variables = dict(variables)
        self._equates = dict(equates)
        self._symbol_offsets = dict(symbol_offsets or self._symbol_offsets)
        self._instruction_highlighter.set_symbols(labels, variables, equates)
        self._raw_instruction_highlighter.set_symbols(labels, variables, equates)
        self.instructions.set_symbol_helpers(labels, variables, equates)
        self.instructions.set_jump_navigation(self._codec, labels, variables, equates)
        if hasattr(self, "raw_instructions"):
            self._render_raw_instructions()

    def visible_size(self) -> int:
        return self._visible_row_count() * ROW_BYTES

    def set_virtual_total_size(self, size: int) -> None:
        if not self._virtual or size == self._total_size:
            return
        self._total_size = max(0, size)
        self._configure_scrollbar()

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
        self._set_editor_text(self.decoded_text, [decode_hex_bytes(row.bytes_text, self._decoded_text_values) for row in self._rows])
        self._set_editor_text(self.instructions, [self._display_instruction(row.instruction) for row in self._rows])
        self._instruction_highlighter.rehighlight()
        self._render_raw_instructions()
        self._render_offsets()
        self._emit_selection_summary()

    def _render_offsets(self) -> None:
        for name, editor in self._offset_editors.items():
            self._set_editor_text(
                editor,
                [self._display_offset(editor, row.offsets.get(name, "")) for row in self._rows],
            )

    def _display_offset(self, editor: QPlainTextEdit, text: str) -> str:
        if text != "-":
            return text
        metrics = editor.fontMetrics()
        available = editor.viewport().width() - (editor.document().documentMargin() * 2)
        padding = max(0, int((available - metrics.horizontalAdvance(text)) / 2))
        spaces = padding // max(1, metrics.horizontalAdvance(" "))
        return f"{' ' * spaces}{text}"

    def _on_scrollbar_changed(self, value: int) -> None:
        if self._updating:
            return
        if not self._virtual:
            self._scroll_static_document(value)
            return
        offset = self._aligned_scroll_offset(value)
        direction = 1 if offset >= self._last_visible_offset else -1
        self._last_visible_offset = offset
        self.visibleWindowRequested.emit(offset, self.visible_size(), direction)

    def _scroll_static_document(self, value: int) -> None:
        offset = self._aligned_scroll_offset(value)
        row_index = offset // ROW_BYTES
        self._visible_start_offset = offset
        self._last_visible_offset = offset
        editors = [*self._offset_editors.values(), self.raw_instructions, self.bytes, self.decoded_text, self.instructions]
        self._syncing_editor_scrollbars = True
        try:
            for editor in editors:
                editor.verticalScrollBar().setValue(row_index)
        finally:
            self._syncing_editor_scrollbars = False

    def _set_editor_text(self, editor: QPlainTextEdit, lines: list[str]) -> None:
        was_updating = self._updating
        self._updating = True
        scroll_value = editor.verticalScrollBar().value()
        try:
            editor.setPlainText("\n".join(lines))
            if not self._virtual:
                editor.verticalScrollBar().setValue(min(scroll_value, editor.verticalScrollBar().maximum()))
            self._remember_editor_text_signature(editor)
        finally:
            self._updating = was_updating

    def _remember_editor_text_signature(self, editor: QPlainTextEdit) -> None:
        self._editor_text_signatures[id(editor)] = self._editor_text_signature(editor)

    def _has_meaningful_editor_change(self, editor: QPlainTextEdit) -> bool:
        return self._editor_text_signature(editor) != self._editor_text_signatures.get(id(editor), "")

    def _editor_text_signature(self, editor: QPlainTextEdit) -> str:
        return "\n".join(
            "".join(line.split())
            for line in editor.toPlainText().split("\n")
        )

    def _display_bytes_text(self, text: str) -> str:
        return normalize_bytes_text(text, self._group_bytes, self._uppercase_bytes)

    def _display_instruction(self, text: str) -> str:
        return normalize_instruction_text(text, self._uppercase_instructions)
