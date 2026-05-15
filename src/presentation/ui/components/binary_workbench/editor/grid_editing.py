from src.core.binary_workbench.mips_r3000a import expand_pseudo_instructions
from src.core.binary_workbench.symbolic_instructions import preserve_symbolic_rows
from src.modules.dtos import BinaryWorkbenchRowDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import (
    labels_from_lines_at_rows,
    labels_from_rows,
)
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import (
    ROW_BYTES,
    address_from_row,
    assembly_for_encoding,
    byte_cursor_position,
    normalize_bytes_text,
    normalize_instruction_text,
)


class GridEditingMixin:
    def _on_bytes_changed(self) -> None:
        if self._updating:
            return
        self._sync_user_rows(self._normalized_bytes_lines(), BINARY_WORKBENCH_TEXT.BYTES)

    def _on_instructions_changed(self) -> None:
        if self._updating:
            return
        self._sync_user_rows(self._normalized_instruction_lines(), BINARY_WORKBENCH_TEXT.INSTRUCTION)

    def edit_origin_kind(self) -> str | None:
        return self._edit_origin_kind

    def _sync_user_rows(self, lines: list[str], origin: str) -> None:
        self._set_last_editor(origin)
        self._dirty_editor_kind = origin
        self._edit_origin_kind = origin
        try:
            self._sync_rows(lines, origin == BINARY_WORKBENCH_TEXT.BYTES)
        finally:
            self._edit_origin_kind = None

    def _sync_rows(self, lines: list[str], editing_bytes: bool) -> None:
        if self._updating:
            return
        old_count = len(self._rows)
        updated = self._byte_rows_from_lines(lines) if editing_bytes else self._instruction_rows_from_lines(lines)
        if updated is None:
            return
        if editing_bytes:
            updated = preserve_symbolic_rows(updated, self._rows, self._labels, self._variables, self._equates, self._codec)
        self._rows = updated
        if not editing_bytes:
            self._set_editing_labels(labels_from_rows(updated))
        if not self._virtual:
            start = self._aligned_scroll_offset(self.scrollbar.value()) // ROW_BYTES
            self._all_rows[start : start + old_count] = updated
            self.rowsChanged.emit(self.export_rows())
        else:
            self.rowsChanged.emit(self._rows)
        target = self.instructions if editing_bytes else self.bytes
        values = [self._display_instruction(row.instruction) for row in self._rows] if editing_bytes else [self._display_bytes_text(row.bytes_text) for row in self._rows]
        self._set_editor_text(target, values)
        self._render_raw_instructions()
        self._emit_selection_summary()
        self._dirty_editor_kind = None

    def _set_editing_labels(self, labels: dict[str, str]) -> None:
        was_updating = self._updating
        self._updating = True
        self._labels = labels
        self._instruction_highlighter.set_symbols(labels, self._variables, self._equates)
        self.instructions.set_symbol_helpers(labels, self._variables, self._equates)
        self._updating = was_updating

    def _byte_rows_from_lines(self, lines: list[str]) -> list[BinaryWorkbenchRowDTO] | None:
        raw = "".join("".join(lines).split())
        if len(raw) % 2:
            return None
        try:
            data = bytes.fromhex(raw)
        except ValueError:
            return None
        rows: list[BinaryWorkbenchRowDTO] = []
        for index, start in enumerate(range(0, len(data), ROW_BYTES)):
            chunk = data[start : start + ROW_BYTES]
            row = self._row_at(index)
            address = address_from_row(row)
            rows.append(BinaryWorkbenchRowDTO(offsets=row.offsets, instruction=self._codec.disassemble(chunk.ljust(ROW_BYTES, b"\x00"), address), bytes_text=self._codec.bytes_text(chunk)))
        return rows

    def rows_encoded_with_symbols(
        self,
        variables: dict[str, str],
        equates: dict[str, str],
        labels: dict[str, str],
    ) -> list[BinaryWorkbenchRowDTO]:
        rows: list[BinaryWorkbenchRowDTO] = []
        for row in self.export_rows():
            address = address_from_row(row)
            assembly = assembly_for_encoding(row.instruction, address, labels, variables, equates)
            data = self._codec.assemble(assembly, address)
            rows.append(
                row
                if data is None
                else BinaryWorkbenchRowDTO(
                    offsets=row.offsets,
                    instruction=row.instruction,
                    bytes_text=self._codec.bytes_text(data),
                )
            )
        return rows

    def _instruction_rows_from_lines(
        self,
        lines: list[str],
        labels: dict[str, str] | None = None,
        variables: dict[str, str] | None = None,
        equates: dict[str, str] | None = None,
    ) -> list[BinaryWorkbenchRowDTO] | None:
        source_rows = [self._row_at(index) for index in range(len(lines))]
        labels = labels_from_lines_at_rows(lines, source_rows) if labels is None else labels
        variables = self._variables if variables is None else variables
        equates = self._equates if equates is None else equates
        rows: list[BinaryWorkbenchRowDTO] = []
        for index, line in enumerate(lines):
            row = source_rows[index]
            address = address_from_row(row)
            assembly = assembly_for_encoding(line, address, labels, variables, equates)
            data = self._codec.assemble(assembly, address)
            if data is None:
                return None
            rows.append(BinaryWorkbenchRowDTO(offsets=row.offsets, instruction=line.rstrip(), bytes_text=self._codec.bytes_text(data)))
        return rows

    def _normalized_bytes_lines(self) -> list[str]:
        text = self.bytes.toPlainText()
        normalized = normalize_bytes_text(text, self._group_bytes, self._uppercase_bytes)
        if normalized != text:
            raw_index = len("".join(text[: self.bytes.textCursor().position()].split()))
            self._set_editor_text(self.bytes, normalized.splitlines())
            cursor = self.bytes.textCursor()
            cursor.setPosition(byte_cursor_position(normalized, raw_index))
            self.bytes.setTextCursor(cursor)
        return normalized.splitlines()

    def _normalized_instruction_lines(self) -> list[str]:
        text = self.instructions.toPlainText()
        normalized = normalize_instruction_text(text, self._uppercase_instructions)
        normalized = "\n".join(expand_pseudo_instructions(normalized.splitlines()))
        normalized = normalize_instruction_text(normalized, self._uppercase_instructions)
        if normalized != text:
            position = self.instructions.textCursor().position()
            self._set_editor_text(self.instructions, normalized.splitlines())
            cursor = self.instructions.textCursor()
            cursor.setPosition(min(position, len(normalized)))
            self.instructions.setTextCursor(cursor)
        return normalized.splitlines()
