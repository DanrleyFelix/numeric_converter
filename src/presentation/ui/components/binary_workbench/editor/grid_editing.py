from src.core.binary_workbench.mips_r3000a import (
    build_source_line_rows,
    editor_mips_instruction,
    expand_pseudo_instructions,
    rebuild_rows_with_offsets,
)
from src.core.binary_workbench.symbolic_instructions import preserve_symbolic_rows
from src.core.binary_workbench.virtual_instruction_reconcile import (
    reconcile_locked_virtual_instructions,
)
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES
from src.modules.constants import HEX_DIGITS
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.cursor_guard import (
    set_cursor_position,
)
from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import labels_from_rows
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import (
    address_from_row,
    normalize_bytes_text,
    normalize_instruction_text,
)


class GridEditingMixin:
    def _on_bytes_changed(self) -> None:
        if self._updating:
            return
        if not self._editor_change_allowed(True):
            self._restore_editor_after_rejected_change(True)
            return
        if not self._has_meaningful_editor_change(self.bytes):
            return
        if not self._bytes_user_edit_in_progress():
            self._normalize_bytes_editor_text()
        self._sync_user_rows(self._normalized_bytes_lines(), BINARY_WORKBENCH_TEXT.BYTES)

    def _on_instructions_changed(self) -> None:
        if self._updating:
            return
        if not self._editor_change_allowed(False):
            self._restore_editor_after_rejected_change(False)
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
        updated = self._byte_rows_from_lines(lines) if editing_bytes else self._instruction_rows_from_lines(lines)
        if updated is None:
            self._restore_editor_after_rejected_change(editing_bytes)
            return
        if not self._rows_change_allowed(updated, editing_bytes):
            self._restore_editor_after_rejected_change(editing_bytes)
            return
        if editing_bytes:
            updated = preserve_symbolic_rows(
                updated,
                self._rows,
                self._labels,
                self._variables,
                self._equates,
                self._codec,
                self._symbol_offsets,
            )
        self._rows = updated
        if not editing_bytes:
            self._set_editing_labels(labels_from_rows(updated))
        if not self._virtual:
            self._all_rows = rebuild_rows_with_offsets(
                updated,
                self._columns or [BINARY_WORKBENCH_TEXT.FILE],
                self._offset_base_text(),
            )
            self._rows = list(self._all_rows)
            self._total_size = len(self._all_rows) * ROW_BYTES
            self._configure_scrollbar()
            self.rowsChanged.emit(self.export_rows())
        else:
            self._total_size = self._expanded_virtual_total_size(updated)
            self._configure_scrollbar()
            self.rowsChanged.emit(self._rows)
        self._render_offsets()
        target = self.instructions if editing_bytes else self.bytes
        values = [self._display_instruction(row.instruction) for row in self._rows] if editing_bytes else [self._display_bytes_text(row.bytes_text) for row in self._rows]
        self._set_editor_text(target, values)
        self._render_raw_instructions()
        if not self._virtual:
            self._scroll_static_document(self.scrollbar.value())
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
        self.instructions.set_jump_navigation(self._codec, labels, self._variables, self._equates)
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
                        instruction=self._bytes_fallback_instruction(row),
                        bytes_text="",
                    )
                )
                continue
            if len(raw) < ROW_BYTES * 2:
                row = self._row_at(len(rows))
                rows.append(
                    BinaryWorkbenchRowDTO(
                        offsets=row.offsets,
                        instruction=self._bytes_fallback_instruction(row),
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

    def _bytes_fallback_instruction(self, row: BinaryWorkbenchRowDTO) -> str:
        return row.instruction if self._locked_virtual_bytes_edit() else ""

    def _locked_virtual_bytes_edit(self) -> bool:
        return self._virtual and not self._edit_rules.allow_byte_shift and not self._free_offset_window()

    def _rows_decoded_after_offset_rebuild(
        self,
        rows: list[BinaryWorkbenchRowDTO],
    ) -> list[BinaryWorkbenchRowDTO]:
        rebuilt = rows if self._virtual else rebuild_rows_with_offsets(
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
        replacement: tuple[int, int, str] | None = None,
    ) -> list[BinaryWorkbenchRowDTO]:
        lines = [row.instruction for row in self.export_rows()]
        if replacement is not None:
            lines = self._instruction_lines_with_replacement(lines, replacement)
        rows = build_source_line_rows(
            lines,
            self._columns or [BINARY_WORKBENCH_TEXT.FILE],
            self._offset_base_text(),
            self._codec,
            self._source_rows_start_offset(),
            labels,
            variables,
            equates,
        )
        return rows or self.export_rows()

    def _instruction_lines_with_replacement(
        self,
        lines: list[str],
        replacement: tuple[int, int, str],
    ) -> list[str]:
        start, end, text = replacement
        block = self.instructions.document().findBlock(start)
        if not block.isValid() or not 0 <= block.blockNumber() < len(lines):
            return lines
        line = lines[block.blockNumber()]
        column_start = max(0, start - block.position())
        column_end = max(column_start, end - block.position())
        lines[block.blockNumber()] = f"{line[:column_start]}{text}{line[column_end:]}"
        return lines

    def _instruction_rows_from_lines(
        self,
        lines: list[str],
        labels: dict[str, str] | None = None,
        variables: dict[str, str] | None = None,
        equates: dict[str, str] | None = None,
    ) -> list[BinaryWorkbenchRowDTO] | None:
        if self._locked_virtual_instruction_edit():
            rows = reconcile_locked_virtual_instructions(
                lines,
                self._rows,
                self._columns or [BINARY_WORKBENCH_TEXT.FILE],
                self._offset_base_text(),
                self._codec,
                self._labels,
                self._variables if variables is None else variables,
                self._equates if equates is None else equates,
            )
            return self._rows_with_instruction_spacing(rows, lines)
        rows = build_source_line_rows(
            lines,
            self._columns or [BINARY_WORKBENCH_TEXT.FILE],
            self._offset_base_text(),
            self._codec,
            self._source_rows_start_offset(),
            labels,
            self._variables if variables is None else variables,
            self._equates if equates is None else equates,
            False,
        )
        rows = self._virtual_instruction_rows_with_previous_bytes(rows) if self._virtual else rows
        return self._rows_with_instruction_spacing(rows, lines)

    def _rows_with_instruction_spacing(
        self,
        rows: list[BinaryWorkbenchRowDTO] | None,
        lines: list[str],
    ) -> list[BinaryWorkbenchRowDTO] | None:
        if rows is None or len(rows) != len(lines):
            return rows
        updated: list[BinaryWorkbenchRowDTO] = []
        for row, line in zip(rows, lines):
            if line != row.instruction and _without_spacing(line) == _without_spacing(row.instruction):
                updated.append(BinaryWorkbenchRowDTO(row.offsets, line, row.bytes_text))
                continue
            updated.append(row)
        return updated

    def _locked_virtual_instruction_edit(self) -> bool:
        return self._virtual and not self._edit_rules.allow_byte_shift and not self._free_offset_window()

    def _source_rows_start_offset(self) -> int:
        return self._visible_start_offset if self._virtual else 0

    def _virtual_instruction_rows_with_previous_bytes(
        self,
        rows: list[BinaryWorkbenchRowDTO] | None,
    ) -> list[BinaryWorkbenchRowDTO] | None:
        if rows is None:
            return None
        updated: list[BinaryWorkbenchRowDTO] = []
        for index, row in enumerate(rows):
            previous = self._row_at(index)
            if row.bytes_text or previous.offsets.get(BINARY_WORKBENCH_TEXT.FILE) == "-":
                updated.append(row)
                continue
            if index >= len(self._rows) and self._row_after_original_boundary(previous):
                updated.append(
                    BinaryWorkbenchRowDTO(
                        offsets=previous.offsets,
                        instruction=row.instruction,
                        bytes_text="",
                    )
                )
                continue
            updated.append(
                BinaryWorkbenchRowDTO(
                    offsets=previous.offsets,
                    instruction=row.instruction,
                    bytes_text=previous.bytes_text,
                )
            )
        return updated

    def _row_after_original_boundary(self, row: BinaryWorkbenchRowDTO) -> bool:
        try:
            return int(row.offsets.get(BINARY_WORKBENCH_TEXT.FILE, "-"), 16) >= self._original_boundary()
        except ValueError:
            return False

    def _bytes_user_edit_in_progress(self) -> bool:
        return self.bytes.hasFocus() or bool(getattr(self.bytes, "_granular_editing", False))

    def _instructions_user_edit_in_progress(self) -> bool:
        return self.instructions.hasFocus() or bool(getattr(self.instructions, "_granular_editing", False))

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
        set_cursor_position(cursor, position + (len(normalized) - len(text)))
        self.bytes.setTextCursor(cursor)

    def _normalized_bytes_line(self, line: str) -> str:
        raw = "".join(char for char in line if char in HEX_DIGITS)
        raw = raw[: ROW_BYTES * 2]
        raw = raw.upper() if self._uppercase_bytes else raw
        normalized = normalize_bytes_text(raw, 1, False)
        if 0 < len(raw) < ROW_BYTES * 2 and len(raw) % 2 == 0:
            return f"{normalized} "
        return normalized

    def _normalized_instruction_lines(self) -> list[str]:
        text = self.instructions.toPlainText()
        formatted = normalize_instruction_text(text, self._uppercase_instructions)
        normalized = "\n".join(expand_pseudo_instructions(formatted.split("\n")))
        normalized = normalize_instruction_text(normalized, self._uppercase_instructions)
        if normalized != text and not self._instructions_user_edit_in_progress():
            self._set_editor_text(self.instructions, normalized.split("\n"))
        return normalized.split("\n")


def _without_spacing(text: str) -> str:
    return "".join(text.split())
