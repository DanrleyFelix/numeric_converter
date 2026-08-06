from __future__ import annotations

from PySide6.QtCore import QTimer

from src.core.binary_workbench.encoding_tables import decode_hex_bytes
from src.core.binary_workbench.mips_r3000a import (
    build_source_line_rows,
    editor_mips_instruction,
    validate_mips_hazards,
)
from src.core.binary_workbench.symbolic_instructions import symbolic_instruction
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO
from src.presentation.ui.components.binary_workbench.constant_groups.timing import (
    BINARY_WORKBENCH_TIMING,
)
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import (
    label_declarations_changed,
)
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import (
    address_from_row,
)


class GridIncrementalEditingMixin:
    """Assemble stable single-line edits without rebuilding unrelated rows."""

    def _setup_incremental_editing(self) -> None:
        self._pending_instruction_lines: list[str] | None = None
        self._incremental_propagation_timer = QTimer(self)
        self._incremental_propagation_timer.setSingleShot(True)
        self._incremental_propagation_timer.setInterval(
            BINARY_WORKBENCH_TIMING.INCREMENTAL_PROPAGATION_MS
        )
        self._incremental_propagation_timer.timeout.connect(
            self._flush_instruction_propagation
        )

    def _handle_instruction_change(self, lines: list[str]) -> None:
        if self._try_single_line_update(lines):
            return
        self._schedule_instruction_propagation(lines)

    def _try_single_line_update(self, lines: list[str]) -> bool:
        if (
            self._virtual
            or len(lines) != len(self._rows)
        ):
            return False
        changed = [
            index
            for index, (row, line) in enumerate(zip(self._rows, lines))
            if self._display_instruction(row.instruction) != line
        ]
        if len(changed) != 1:
            return False
        index = changed[0]
        previous = self._rows[index]
        current = self._single_instruction_row(index, lines[index])
        if current is None or bool(previous.bytes_text) != bool(current.bytes_text):
            return False
        labels_changed = label_declarations_changed([previous], [current])
        self._apply_single_instruction_row(index, current)
        if labels_changed:
            self._refresh_label_folding(anchor_row=index)
            self._schedule_instruction_propagation(lines)
        else:
            self._schedule_instruction_propagation(None)
        return True

    def _try_single_byte_update(
        self,
        lines: list[str],
        index_hint: int | None = None,
    ) -> bool:
        """Commit one complete Bytes row without rebuilding every projection."""

        if self._virtual or len(lines) != len(self._rows):
            return False
        changed = (
            [index_hint]
            if index_hint is not None
            and 0 <= index_hint < len(self._rows)
            and _canonical_bytes(self._display_bytes_row(self._rows[index_hint]))
            != _canonical_bytes(lines[index_hint])
            else [
                index
                for index, (row, line) in enumerate(zip(self._rows, lines))
                if _canonical_bytes(self._display_bytes_row(row))
                != _canonical_bytes(line)
            ]
        )
        if len(changed) != 1:
            return False
        index = changed[0]
        row = self._complete_byte_row(index, lines[index], self._source_offset_before_row(index))
        if row is None:
            return False
        coordinator = getattr(self, "_consistency_coordinator", None)
        if coordinator is None or not coordinator.enabled():
            return False
        coordinator.accept_bytes_line(index, row)
        self._remember_editor_text_signature(self.bytes)
        self._dirty_editor_kind = None
        return True

    def _try_multiple_byte_update(self, lines: list[str]) -> bool:
        """Commit complete changed Bytes rows without rebuilding the document."""

        if self._virtual or len(lines) != len(self._rows):
            return False
        changed = [
            index
            for index, (row, line) in enumerate(zip(self._rows, lines))
            if _canonical_bytes(self._display_bytes_row(row))
            != _canonical_bytes(line)
        ]
        if len(changed) < 2:
            return False
        changed_set = set(changed)
        address = self._source_rows_start_offset()
        rows: list[tuple[int, BinaryWorkbenchRowDTO]] = []
        for index, previous in enumerate(self._rows):
            if index in changed_set:
                row = self._complete_byte_row(index, lines[index], address)
                if row is None:
                    return False
                rows.append((index, row))
                address += ROW_BYTES
            elif previous.bytes_text:
                address += ROW_BYTES
        coordinator = getattr(self, "_consistency_coordinator", None)
        if coordinator is None or not coordinator.enabled():
            return False
        coordinator.accept_bytes_lines(tuple(rows))
        self._remember_editor_text_signature(self.bytes)
        self._dirty_editor_kind = None
        return True

    def _complete_byte_row(
        self,
        index: int,
        line: str,
        address: int,
    ) -> BinaryWorkbenchRowDTO | None:
        """Decode one complete Bytes line while preserving source annotations."""

        raw = _canonical_bytes(line)
        if len(raw) != ROW_BYTES * 2:
            return None
        try:
            data = bytes.fromhex(raw)
        except ValueError:
            return None
        previous = self._rows[index]
        offsets = {
            name: f"0x{address + (0 if name == BINARY_WORKBENCH_TEXT.FILE else int(base, 0)):08X}"
            for name, base in self._offset_base_text().items()
        }
        decoded = editor_mips_instruction(self._codec.disassemble(data, address), address)
        instruction = (
            symbolic_instruction(
                decoded,
                previous.instruction,
                self._codec.bytes_text(data),
                address,
                self._labels,
                self._variables,
                self._equates,
                self._codec,
            )
            if previous.instruction
            else decoded
        )
        return BinaryWorkbenchRowDTO(
            offsets,
            instruction,
            self._codec.bytes_text(data),
            previous.original_instruction,
            previous.original_bytes_text,
        )

    def _single_instruction_row(
        self,
        index: int,
        line: str,
    ) -> BinaryWorkbenchRowDTO | None:
        offset = self._source_offset_before_row(index)
        rows = build_source_line_rows(
            [line],
            self._columns or [BINARY_WORKBENCH_TEXT.FILE],
            self._offset_base_text(),
            self._codec,
            offset,
            self._labels,
            self._variables,
            self._equates,
            False,
        )
        if rows is None or len(rows) != 1:
            return None
        rows = self._validated_standard_jump_rows(rows, [line])
        row = rows[0] if rows else None
        if row is None or not self._jump_reference_offset:
            return row
        symbols = self._reference_jump_symbols(
            self._labels,
            self._variables,
            self._equates,
        )
        normalized = self._reference_jump_line(line, symbols)
        if normalized == line:
            return row
        encoded = build_source_line_rows(
            [normalized],
            self._columns or [BINARY_WORKBENCH_TEXT.FILE],
            self._offset_base_text(),
            self._codec,
            offset,
            self._labels,
            self._variables,
            self._equates,
            True,
        )
        if not encoded:
            return row
        return BinaryWorkbenchRowDTO(encoded[0].offsets, line, encoded[0].bytes_text)

    def _source_offset_before_row(self, index: int) -> int:
        previous = self._rows[index] if index < len(self._rows) else None
        if previous is not None and previous.bytes_text:
            return address_from_row(previous)
        return self._source_rows_start_offset() + sum(
            ROW_BYTES for row in self._rows[:index] if row.bytes_text
        )

    def _apply_single_instruction_row(
        self,
        index: int,
        row: BinaryWorkbenchRowDTO,
    ) -> None:
        self._rows = [*self._rows[:index], row, *self._rows[index + 1 :]]
        self._all_rows = list(self._rows)
        self._set_editor_line(self.bytes, index, self._display_bytes_row(row))
        self._set_editor_line(
            self.decoded_text,
            index,
            self._display_decoded_row(row),
        )
        raw = self._display_raw_row(row)
        self._set_editor_line(self.raw_instructions, index, raw)
        self._emit_rows_changed(self._all_rows, deferred=True)
        self._emit_selection_summary()
        self._remember_editor_text_signature(self.instructions)
        self._dirty_editor_kind = None

    def _schedule_instruction_propagation(
        self,
        lines: list[str] | None,
    ) -> None:
        if lines is not None:
            self._pending_instruction_lines = list(lines)
        self._incremental_propagation_timer.start()

    def _flush_instruction_propagation(self) -> None:
        lines = self._pending_instruction_lines
        self._pending_instruction_lines = None
        if lines is None:
            self._refresh_instruction_hazards()
            return
        if self._bounded_refresh_available(lines):
            previous_origin = self._edit_origin_kind
            self._edit_origin_kind = BINARY_WORKBENCH_TEXT.INSTRUCTION
            try:
                self._refresh_bounded_source_rows(lines)
            finally:
                self._edit_origin_kind = previous_origin
            return
        self._sync_user_rows(lines, BINARY_WORKBENCH_TEXT.INSTRUCTION)

    def _refresh_instruction_hazards(self) -> None:
        self.raw_instructions.set_hazard_extra_selections([])
        self._apply_instruction_hazards(
            validate_mips_hazards([row.instruction for row in self._rows])
        )

    def _cancel_incremental_instruction_update(self) -> None:
        self._pending_instruction_lines = None
        self._incremental_propagation_timer.stop()
        coordinator = getattr(self, "_consistency_coordinator", None)
        if coordinator is not None:
            coordinator.cancel_pending()


def _canonical_bytes(value: str) -> str:
    return "".join(value.split()).upper()
