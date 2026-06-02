from PySide6.QtWidgets import QPlainTextEdit

from src.modules.dtos import BinaryWorkbenchRowDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import (
    ROW_BYTES,
    normalize_bytes_text,
    normalize_instruction_text,
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
    ) -> None:
        offsets = [name for name in columns if name not in {BINARY_WORKBENCH_TEXT.BYTES, BINARY_WORKBENCH_TEXT.INSTRUCTION}]
        self._sync_offset_columns(offsets)
        self._group_bytes = group_bytes if group_bytes in {1, 2, 4} else 1
        self._uppercase_bytes = uppercase_bytes
        self._uppercase_instructions = uppercase_instructions
        self._virtual = virtual
        self._total_size = total_size if virtual else len(rows) * ROW_BYTES
        self._all_rows = [] if virtual else list(rows)
        self._dirty_editor_kind = None
        self._visible_start_offset = start_offset
        self._last_visible_offset = start_offset
        self._configure_scrollbar()
        self.render_rows(rows, start_offset) if virtual else self._render_static_window()
        self._schedule_layout_refresh()

    def render_rows(self, rows: list[BinaryWorkbenchRowDTO], start_offset: int) -> None:
        self._rows = list(rows)
        self._visible_start_offset = start_offset
        self._render()
        self._dirty_editor_kind = None

    def set_symbols(self, labels: dict[str, str], variables: dict[str, str], equates: dict[str, str]) -> None:
        self._labels = dict(labels)
        self._variables = dict(variables)
        self._equates = dict(equates)
        self._instruction_highlighter.set_symbols(labels, variables, equates)
        self._raw_instruction_highlighter.set_symbols(labels, variables, equates)
        self.instructions.set_symbol_helpers(labels, variables, equates)
        if hasattr(self, "raw_instructions"):
            self._render_raw_instructions()

    def visible_size(self) -> int:
        return self._visible_row_count() * ROW_BYTES

    def export_rows(self) -> list[BinaryWorkbenchRowDTO]:
        return list(self._all_rows if not self._virtual else self._rows)

    def set_visible_offset(self, offset: int) -> None:
        target = min(max(0, offset), self.scrollbar.maximum())
        if not self._virtual and self._offset_is_visible(target):
            return
        if self.scrollbar.value() == target:
            self._on_scrollbar_changed(target)
            return
        self.scrollbar.setValue(target)

    def _offset_is_visible(self, offset: int) -> bool:
        return self._visible_start_offset <= offset < self._visible_start_offset + (len(self._rows) * ROW_BYTES)

    def _render(self) -> None:
        self._resize_editors()
        self._set_editor_text(self.bytes, [self._display_bytes_text(row.bytes_text) for row in self._rows])
        self._set_editor_text(self.instructions, [self._display_instruction(row.instruction) for row in self._rows])
        self._instruction_highlighter.rehighlight()
        self._render_raw_instructions()
        self._render_offsets()
        self._emit_selection_summary()

    def _render_offsets(self) -> None:
        for name, editor in self._offset_editors.items():
            self._set_editor_text(editor, [row.offsets.get(name, "") for row in self._rows])

    def _render_static_window(self) -> None:
        count = self._visible_row_count()
        start = self._aligned_scroll_offset(self.scrollbar.value()) // ROW_BYTES
        self._rows = self._all_rows[start : start + count]
        self._visible_start_offset = start * ROW_BYTES
        self._render()

    def _on_scrollbar_changed(self, value: int) -> None:
        if self._updating:
            return
        if not self._virtual:
            self._render_static_window()
            return
        offset = self._aligned_scroll_offset(value)
        direction = 1 if offset >= self._last_visible_offset else -1
        self._last_visible_offset = offset
        self.visibleWindowRequested.emit(offset, self.visible_size(), direction)

    def _set_editor_text(self, editor: QPlainTextEdit, lines: list[str]) -> None:
        was_updating = self._updating
        self._updating = True
        try:
            editor.setPlainText("\n".join(lines))
        finally:
            self._updating = was_updating

    def _display_bytes_text(self, text: str) -> str:
        return normalize_bytes_text(text, self._group_bytes, self._uppercase_bytes)

    def _display_instruction(self, text: str) -> str:
        return normalize_instruction_text(text, self._uppercase_instructions)
