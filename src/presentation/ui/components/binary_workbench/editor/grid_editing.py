from src.core.binary_workbench.mips_r3000a import (
    build_source_line_rows,
    editor_mips_instruction,
    expand_pseudo_instructions,
    instruction_code,
    rebuild_rows_with_offsets,
)
from src.core.binary_workbench.symbolic_instructions import preserve_symbolic_rows
from src.modules.dtos import BinaryWorkbenchRowDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import labels_from_rows
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import (
    ROW_BYTES,
    address_from_row,
    assembly_for_encoding,
    normalize_bytes_text,
    normalize_instruction_text,
)


class GridEditingMixin:
    def _on_bytes_changed(self) -> None:
        if self._updating:
            return
        if not self._has_meaningful_editor_change(self.bytes):
            return
        self._normalize_bytes_editor_text()
        self._sync_user_rows(self._normalized_bytes_lines(), BINARY_WORKBENCH_TEXT.BYTES)

    def _on_instructions_changed(self) -> None:
        if self._updating:
            return
        if not self._has_meaningful_editor_change(self.instructions):
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
            self._all_rows = rebuild_rows_with_offsets(
                self._all_rows,
                self._columns or [BINARY_WORKBENCH_TEXT.FILE],
                self._offset_base_text(),
            )
            self._rows = self._all_rows[start : start + len(updated)]
            self._total_size = len(self._all_rows) * ROW_BYTES
            self._configure_scrollbar()
            self.rowsChanged.emit(self.export_rows())
        else:
            self.rowsChanged.emit(self._rows)
        self._render_offsets()
        target = self.instructions if editing_bytes else self.bytes
        values = [self._display_instruction(row.instruction) for row in self._rows] if editing_bytes else [self._display_bytes_text(row.bytes_text) for row in self._rows]
        self._set_editor_text(target, values)
        self._render_raw_instructions()
        self._emit_selection_summary()
        source = self.bytes if editing_bytes else self.instructions
        self._remember_editor_text_signature(source)
        self._dirty_editor_kind = None

    def _offset_base_text(self) -> dict[str, str]:
        return {
            name: f"0x{base:08X}"
            for name, base in self._offset_bases().items()
        }

    def _set_editing_labels(self, labels: dict[str, str]) -> None:
        was_updating = self._updating
        self._updating = True
        self._labels = labels
        self._instruction_highlighter.set_symbols(labels, self._variables, self._equates)
        self.instructions.set_symbol_helpers(labels, self._variables, self._equates)
        self._updating = was_updating

    def _byte_rows_from_lines(self, lines: list[str]) -> list[BinaryWorkbenchRowDTO] | None:
        rows: list[BinaryWorkbenchRowDTO] = []
        for line in lines:
            raw = "".join(line.split())
            if not raw:
                row = self._row_at(len(rows))
                rows.append(
                    BinaryWorkbenchRowDTO(
                        offsets=row.offsets,
                        instruction="",
                        bytes_text="",
                    )
                )
                continue
            if len(raw) < ROW_BYTES * 2:
                row = self._row_at(len(rows))
                rows.append(
                    BinaryWorkbenchRowDTO(
                        offsets=row.offsets,
                        instruction="",
                        bytes_text="",
                    )
                )
                continue
            if len(raw) != ROW_BYTES * 2:
                return None
            try:
                data = bytes.fromhex(raw)
            except ValueError:
                return None
            for start in range(0, len(data), ROW_BYTES):
                chunk = data[start : start + ROW_BYTES]
                row = self._row_at(len(rows))
                rows.append(
                    BinaryWorkbenchRowDTO(
                        offsets=row.offsets,
                        instruction=row.instruction,
                        bytes_text=self._codec.bytes_text(chunk),
                    )
                )
        return self._rows_decoded_after_offset_rebuild(rows)

    def _rows_decoded_after_offset_rebuild(
        self,
        rows: list[BinaryWorkbenchRowDTO],
    ) -> list[BinaryWorkbenchRowDTO]:
        rebuilt = rebuild_rows_with_offsets(
            rows,
            self._columns or [BINARY_WORKBENCH_TEXT.FILE],
            self._offset_base_text(),
        )
        decoded: list[BinaryWorkbenchRowDTO] = []
        for row in rebuilt:
            if not row.bytes_text:
                decoded.append(row)
                continue
            address = address_from_row(row)
            data = bytes.fromhex(row.bytes_text.replace(" ", ""))
            raw_instruction = self._codec.disassemble(data.ljust(ROW_BYTES, b"\x00"), address)
            decoded.append(
                BinaryWorkbenchRowDTO(
                    offsets=row.offsets,
                    instruction=editor_mips_instruction(raw_instruction, address),
                    bytes_text=row.bytes_text,
                )
            )
        return decoded

    def rows_encoded_with_symbols(
        self,
        variables: dict[str, str],
        equates: dict[str, str],
        labels: dict[str, str],
    ) -> list[BinaryWorkbenchRowDTO]:
        rows: list[BinaryWorkbenchRowDTO] = []
        for row in self.export_rows():
            if not instruction_code(row.instruction):
                rows.append(row)
                continue
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
        return build_source_line_rows(
            lines,
            self._columns or [BINARY_WORKBENCH_TEXT.FILE],
            self._offset_base_text(),
            self._codec,
            self._visible_start_offset,
            labels,
            self._variables if variables is None else variables,
            self._equates if equates is None else equates,
            True,
        )

    def _normalized_bytes_lines(self) -> list[str]:
        lines: list[str] = []
        for line in self.bytes.toPlainText().split("\n"):
            lines.append(self._normalized_bytes_line(line))
        return lines

    def _normalize_bytes_editor_text(self) -> None:
        text = self.bytes.toPlainText()
        normalized = "\n".join(
            self._normalized_bytes_line(line)
            for line in text.split("\n")
        )
        if normalized == text:
            return
        position = self.bytes.textCursor().position()
        self._set_editor_text(self.bytes, normalized.split("\n"))
        cursor = self.bytes.textCursor()
        cursor.setPosition(min(position + (len(normalized) - len(text)), len(normalized)))
        self.bytes.setTextCursor(cursor)

    def _normalized_bytes_line(self, line: str) -> str:
        raw = "".join(char for char in line if char in "0123456789abcdefABCDEF")
        raw = raw[: ROW_BYTES * 2]
        raw = raw.upper() if self._uppercase_bytes else raw
        normalized = normalize_bytes_text(raw, 1, False)
        if 0 < len(raw) < ROW_BYTES * 2 and len(raw) % 2 == 0:
            return f"{normalized} "
        return normalized

    def _normalized_instruction_lines(self) -> list[str]:
        text = self.instructions.toPlainText()
        normalized = normalize_instruction_text(text, self._uppercase_instructions)
        normalized = "\n".join(expand_pseudo_instructions(normalized.split("\n")))
        normalized = normalize_instruction_text(normalized, self._uppercase_instructions)
        if normalized != text:
            position = self.instructions.textCursor().position()
            self._set_editor_text(self.instructions, normalized.split("\n"))
            cursor = self.instructions.textCursor()
            cursor.setPosition(min(position, len(normalized)))
            self.instructions.setTextCursor(cursor)
        return normalized.split("\n")
