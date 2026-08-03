from __future__ import annotations

from src.core.binary_workbench.encoding_tables import decode_hex_bytes
from src.core.binary_workbench.incremental_refresh import (
    build_source_refresh_rows,
    source_refresh_window,
)
from src.core.binary_workbench.mips_r3000a import (
    MipsHazard,
    validate_mips_hazards,
)
from src.core.binary_workbench.mips_r3000a.comments import strip_comment
from src.core.binary_workbench.mips_r3000a.source_line_rows import split_label
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_ASSEMBLY_REFRESH_WINDOW_BYTES as REFRESH_BYTES,
    BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES,
)
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import address_from_row


class GridRefreshWindowMixin:
    """Bound forced source refreshes to the 4 KB region around the viewport."""

    def _setup_refresh_window(self) -> None:
        self._last_assembly_refresh_window: tuple[int, int] | None = None
        self._assembly_refresh_warning_emitted = False

    def _recalculate_instruction_view(self, lines: list[str]) -> None:
        self._cancel_incremental_instruction_update()
        if not self._bounded_refresh_available(lines):
            self._last_assembly_refresh_window = None
            self._assembly_refresh_warning_emitted = False
            self._sync_user_rows(lines, BINARY_WORKBENCH_TEXT.INSTRUCTION, True)
            return
        self._refresh_bounded_source_rows(lines)

    def _bounded_refresh_available(self, lines: list[str]) -> bool:
        return (
            not self._virtual
            and self._edit_rules.allow_byte_shift
            and len(lines) == len(self._rows)
            and sum(bool(row.bytes_text) for row in self._rows) * ROW_BYTES
            > REFRESH_BYTES
        )

    def _refresh_bounded_source_rows(self, lines: list[str]) -> None:
        anchor = self._scroll_anchor_source_row()
        if anchor is None:
            anchor = self.instructions.textCursor().blockNumber()
        window = source_refresh_window(self._rows, anchor)
        old_rows = self._rows[window.first_row : window.last_row]
        local_lines = lines[window.first_row : window.last_row]
        old_names = {
            name.casefold()
            for row in old_rows
            if (name := split_label(strip_comment(row.instruction).strip())[0])
        }
        outside_labels = {
            name: value
            for name, value in self._labels.items()
            if name.casefold() not in old_names
        }
        rows, labels = self._build_refresh_rows(
            local_lines,
            window.first_byte,
            outside_labels,
        )
        rows = self._validated_standard_jump_rows(rows, local_lines)
        if rows is None:
            return
        rows = self._rows_with_instruction_spacing(rows, local_lines)
        if rows is None or len(rows) != len(local_lines):
            return
        self._rows = [
            *self._rows[: window.first_row],
            *rows,
            *self._rows[window.last_row :],
        ]
        self._all_rows = list(self._rows)
        block_range = (window.first_row, window.last_row)
        self._set_editing_labels(labels, block_range)
        self._render_bounded_rows(*block_range)
        self._refresh_bounded_hazards(*block_range)
        self._refresh_jump_navigation()
        self._emit_rows_changed(self._all_rows, deferred=True)
        self._remember_editor_text_signature(self.instructions)
        self._last_assembly_refresh_window = (
            window.first_byte,
            window.last_byte,
        )
        self._assembly_refresh_warning_emitted = False
        self._dirty_editor_kind = None

    def _build_refresh_rows(
        self,
        lines: list[str],
        start_offset: int,
        outside_labels: dict[str, str],
    ) -> tuple[list[BinaryWorkbenchRowDTO] | None, dict[str, str]]:
        encoded_lines = list(lines)
        labels = dict(self._labels)
        rows = None
        passes = 3 if self._jump_reference_offset else 1
        for _ in range(passes):
            symbols = self._reference_jump_symbols(
                labels,
                self._variables,
                self._equates,
            )
            encoded_lines = [
                self._reference_jump_line(line, symbols)
                for line in lines
            ]
            rows, updated_labels = build_source_refresh_rows(
                encoded_lines,
                self._columns or [BINARY_WORKBENCH_TEXT.FILE],
                self._offset_base_text(),
                self._codec,
                start_offset,
                outside_labels,
                self._variables,
                self._equates,
            )
            if rows is None or updated_labels == labels:
                labels = updated_labels
                break
            labels = updated_labels
        if rows is not None and encoded_lines != lines:
            rows = [
                BinaryWorkbenchRowDTO(row.offsets, line, row.bytes_text)
                for row, line in zip(rows, lines)
            ]
        return rows, labels

    def _render_bounded_rows(self, first: int, last: int) -> None:
        hidden = self._folded_hidden_rows() if self._label_folding_enabled else set()
        for index in range(first, last):
            row = self._rows[index]
            self._set_editor_line(
                self.bytes,
                index,
                self._display_bytes_text(row.bytes_text),
            )
            self._set_editor_line(
                self.decoded_text,
                index,
                decode_hex_bytes(row.bytes_text, self._decoded_text_values),
            )
            raw = self._raw_instruction_from_bytes(row.bytes_text, address_from_row(row))
            self._set_editor_line(self.raw_instructions, index, raw)
            for name, editor in self._offset_editors.items():
                value = self._folded_offset_text(
                    index,
                    name,
                    row.offsets.get(name, ""),
                )
                self._set_editor_line(editor, index, self._display_offset(editor, value))
        if hidden:
            for editor in self._fold_editors():
                self._apply_hidden_rows(editor, hidden)

    def _refresh_bounded_hazards(self, first: int, last: int) -> None:
        hazard_first = max(0, first - 1)
        hazards = validate_mips_hazards(
            [row.instruction for row in self._rows[hazard_first:last]]
        )
        self.raw_instructions.set_hazard_extra_selections([])
        self._apply_instruction_hazards(
            [
                MipsHazard(
                    item.line_index + hazard_first,
                    item.severity,
                    item.message,
                )
                for item in hazards
            ]
        )

    def _warn_if_assembly_refresh_needed(self) -> None:
        window = self._last_assembly_refresh_window
        if window is None or self._assembly_refresh_warning_emitted:
            return
        offset = self._viewport_file_offset()
        if window[0] <= offset < window[1]:
            return
        self._assembly_refresh_warning_emitted = True
        self.commandWarningRequested.emit(
            BINARY_WORKBENCH_TEXT.STATUS_ASSEMBLY_REFRESH_REQUIRED
        )

    def _viewport_file_offset(self) -> int:
        anchor = self._scroll_anchor_source_row() or 0
        for row in self._rows[anchor:]:
            if row.bytes_text:
                return address_from_row(row)
        return sum(bool(row.bytes_text) for row in self._rows) * ROW_BYTES
