import re

from src.core.binary_workbench.byte_editing import (
    ByteEditViolation,
    ByteRowAccess,
    aligned_source_indices,
    byte_row_policy,
    byte_lines_ready_for_commit,
)
from src.core.binary_workbench.mips_r3000a import (
    build_source_line_rows,
    editor_mips_instruction,
    rebuild_rows_with_offsets,
)
from src.core.binary_workbench.mips_r3000a.source_line_rows import instruction_code
from src.core.binary_workbench.mips_r3000a.symbol_resolver import MipsSymbolResolver
from src.core.binary_workbench.mips_r3000a.codec import JUMP_NAVIGATION_BASE
from src.core.binary_workbench.mips_r3000a.comments import split_comment
from src.core.binary_workbench.symbolic_instructions import (
    preserve_symbolic_rows,
    preserved_source_annotation,
)
from src.core.binary_workbench.row_structure import (
    file_offset_layout_changed,
    structural_offset_delta,
)
from src.core.binary_workbench.virtual_instruction_reconcile import (
    reconcile_locked_virtual_instructions,
)
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES
from src.modules.constants import HEX_DIGITS, HEX_DIGIT_PATTERN
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.cursor_guard import (
    set_cursor_position,
)
from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import (
    label_declarations_changed,
    labels_from_rows,
)
from src.presentation.ui.components.binary_workbench.editor.syntax_tokens import (
    address_from_row,
    normalize_bytes_text,
    normalize_instruction_text,
)


REFERENCE_JUMP_TARGET = re.compile(
    rf"\b(?P<mnemonic>j|jal)\s+&(?P<target>[@_]?[A-Za-z_][A-Za-z0-9_]*|[-+]?(?:0x{HEX_DIGIT_PATTERN}+|\d+))",
    re.IGNORECASE,
)
STANDARD_JUMP_TARGET = re.compile(
    rf"\b(?:j|jal)\s+(?P<target>[-+]?(?:0x{HEX_DIGIT_PATTERN}+|\d+))",
    re.IGNORECASE,
)


class GridEditingMixin:
    def _on_bytes_changed(self) -> None:
        if (
            self._updating
            or self._syncing_editor_change
            or self.bytes.crossing_derived_projection_history()
        ):
            return
        if not self._editor_change_allowed(True):
            self._restore_editor_after_rejected_change(True)
            return
        if not self._has_meaningful_editor_change(self.bytes):
            return
        self._syncing_editor_change = True
        try:
            block_hint = self._bytes_edit_block_hint
            self._bytes_edit_block_hint = None
            self._active_bytes_alignment_hint = self._bytes_edit_alignment_hint
            # An incomplete character edit has not changed the authoritative
            # Assembly model yet. Keep valid deferred viewport/Symbol work;
            # the eventual Bytes commit invalidates it through the coordinator.
            self._cancel_incremental_instruction_update(cancel_consistency=False)
            if not self._bytes_user_edit_in_progress():
                self._normalize_bytes_editor_text()
            if self._stage_or_commit_single_byte_block(block_hint):
                return
            if self._try_bytes_structural_history_update():
                return
            lines = self._normalized_bytes_lines()
            if self._try_bytes_structure_update(lines):
                return
            if self._stage_or_commit_single_byte_event(lines, block_hint):
                return
            if not self._byte_lines_change_allowed(lines):
                self._restore_editor_after_rejected_change(True)
                return
            previous = [self._display_bytes_row(row) for row in self._rows]
            if not byte_lines_ready_for_commit(
                previous,
                lines,
                ROW_BYTES,
                self._active_bytes_alignment_hint,
            ):
                self._bytes_staged_incomplete = True
                self._bytes_staged_block = self.bytes.textCursor().blockNumber()
                self._set_last_editor(BINARY_WORKBENCH_TEXT.BYTES)
                return
            self._bytes_staged_incomplete = False
            self._bytes_staged_block = None
            if self._try_single_byte_update(lines):
                return
            if self._try_multiple_byte_update(lines):
                return
            self._byte_transition_validated = True
            try:
                self._sync_user_rows(lines, BINARY_WORKBENCH_TEXT.BYTES)
            finally:
                self._byte_transition_validated = False
        finally:
            self._active_bytes_alignment_hint = None
            self._bytes_edit_alignment_hint = None
            self._syncing_editor_change = False

    def _stage_or_commit_single_byte_block(self, index: int | None) -> bool:
        """Keep ordinary Bytes typing proportional to the edited block.

        Reading ``QPlainTextEdit.toPlainText()`` here made every Backspace scan
        the complete file. Structural and multi-line edits still fall through
        to the aggregated document path below.
        """

        if (
            index is None
            or not 0 <= index < len(self._rows)
            or self.bytes.document().blockCount() != len(self._rows)
        ):
            return False
        block = self.bytes.document().findBlockByNumber(index)
        if not block.isValid():
            return False
        line = self._normalized_bytes_line(block.text())
        policy = byte_row_policy(
            self._rows[index].instruction,
            bool(self._rows[index].bytes_text),
        )
        if policy.access is ByteRowAccess.ASSEMBLY_ONLY:
            self._emit_byte_edit_warning(ByteEditViolation.ASSEMBLY_ONLY)
            self._restore_editor_after_rejected_change(True)
            return True
        raw = "".join(line.split())
        if len(raw) < ROW_BYTES * 2 and all(character in HEX_DIGITS for character in raw):
            self._bytes_staged_incomplete = True
            self._bytes_staged_block = index
            self._set_last_editor(BINARY_WORKBENCH_TEXT.BYTES)
            return True
        if len(raw) != ROW_BYTES * 2:
            return False
        current = self._complete_byte_row(
            index,
            line,
            self._source_offset_before_row(index),
        )
        coordinator = getattr(self, "_consistency_coordinator", None)
        if current is None or coordinator is None or not coordinator.enabled():
            return False
        coordinator.accept_bytes_line(index, current)
        self._bytes_staged_incomplete = False
        self._bytes_staged_block = None
        self._remember_editor_text_signature(self.bytes)
        self._dirty_editor_kind = None
        return True

    def _stage_or_commit_single_byte_event(
        self,
        lines: list[str],
        index: int | None,
    ) -> bool:
        """Handle a preflight-proven one-line event without scanning all rows."""

        if (
            index is None
            or not 0 <= index < len(self._rows)
            or len(lines) != len(self._rows)
        ):
            return False
        policy = byte_row_policy(
            self._rows[index].instruction,
            bool(self._rows[index].bytes_text),
        )
        if policy.access is ByteRowAccess.ASSEMBLY_ONLY:
            self._emit_byte_edit_warning(ByteEditViolation.ASSEMBLY_ONLY)
            self._restore_editor_after_rejected_change(True)
            return True
        raw = "".join(lines[index].split())
        if len(raw) < ROW_BYTES * 2 and all(character in HEX_DIGITS for character in raw):
            self._bytes_staged_incomplete = True
            self._bytes_staged_block = index
            self._set_last_editor(BINARY_WORKBENCH_TEXT.BYTES)
            return True
        if len(raw) == ROW_BYTES * 2 and self._try_single_byte_update(lines, index):
            self._bytes_staged_incomplete = False
            self._bytes_staged_block = None
            return True
        return False

    def _on_instructions_changed(self) -> None:
        if (
            self._updating
            or self._syncing_editor_change
            or self.instructions.crossing_derived_projection_history()
        ):
            return
        if not self._editor_change_allowed(False):
            self._restore_editor_after_rejected_change(False)
            return
        if not self._has_meaningful_editor_change(self.instructions):
            return
        coordinator = getattr(self, "_consistency_coordinator", None)
        if coordinator is not None and coordinator.enabled():
            coordinator.note_text_changed()
            return
        self._syncing_editor_change = True
        try:
            lines = self._normalized_instruction_lines()
            if not self._instructions_user_edit_in_progress():
                self._sync_user_rows(lines, BINARY_WORKBENCH_TEXT.INSTRUCTION)
            else:
                self._set_last_editor(BINARY_WORKBENCH_TEXT.INSTRUCTION)
                self._dirty_editor_kind = BINARY_WORKBENCH_TEXT.INSTRUCTION
                self._edit_origin_kind = BINARY_WORKBENCH_TEXT.INSTRUCTION
                self._handle_instruction_change(lines)
        finally:
            self._edit_origin_kind = None
            self._syncing_editor_change = False
        # Legacy/rule-locked editing has no coordinator flush.  Publish one
        # persistence event only after its synchronous transaction commits.
        self.assemblyTextChanged.emit()

    def edit_origin_kind(self) -> str | None:
        return self._edit_origin_kind

    def _sync_user_rows(
        self,
        lines: list[str],
        origin: str,
        force_recalculation: bool = False,
    ) -> None:
        self._set_last_editor(origin)
        self._dirty_editor_kind = origin
        self._edit_origin_kind = origin
        try:
            self._sync_rows(
                lines,
                origin == BINARY_WORKBENCH_TEXT.BYTES,
                force_recalculation,
            )
        finally:
            self._edit_origin_kind = None

    def recalculate_labels_and_branches(self) -> None:
        """Refresh the active source region and its shared label snapshot."""

        coordinator = getattr(self, "_consistency_coordinator", None)
        if coordinator is not None and coordinator.enabled():
            coordinator.force_refresh()
            return
        self._recalculate_instruction_view(self._normalized_instruction_lines())

    def _sync_rows(
        self,
        lines: list[str],
        editing_bytes: bool,
        force_recalculation: bool = False,
    ) -> None:
        if self._updating:
            return
        if editing_bytes and not self._byte_lines_change_allowed(lines):
            self._restore_editor_after_rejected_change(True)
            return
        updated = self._byte_rows_from_lines(lines) if editing_bytes else self._instruction_rows_from_lines(lines)
        if updated is None:
            self._restore_editor_after_rejected_change(editing_bytes)
            return
        if not self._rows_change_allowed(updated, editing_bytes):
            self._restore_editor_after_rejected_change(editing_bytes)
            return
        if editing_bytes:
            updated = self._preserve_bytes_rows(updated)
        offset_delta = structural_offset_delta(self._rows, updated)
        label_structure_changed = label_declarations_changed(self._rows, updated)
        offset_layout_changed = file_offset_layout_changed(self._rows, updated)
        labels = labels_from_rows(updated) if (
            offset_layout_changed or label_structure_changed or force_recalculation
        ) else self._labels
        labels_changed = labels != self._labels
        incomplete_bytes_edit = editing_bytes and _has_incomplete_byte_rows(updated)
        self._rows = updated
        rows_changed_payload: list[BinaryWorkbenchRowDTO] | None = None
        if not editing_bytes:
            self._last_assembly_refresh_window = None
            self._assembly_refresh_warning_emitted = False
        if labels_changed or force_recalculation:
            self._set_editing_labels(labels)
        if not self._virtual:
            self._all_rows = list(updated) if (
                not editing_bytes and self._preserve_instruction_offsets()
            ) else rebuild_rows_with_offsets(
                updated,
                self._columns or [BINARY_WORKBENCH_TEXT.FILE],
                self._offset_base_text(),
            )
            self._rows = list(self._all_rows)
            self._total_size = len(self._all_rows) * ROW_BYTES
            self._configure_scrollbar()
            rows_changed_payload = self.export_rows()
            if not editing_bytes:
                self._emit_rows_changed(rows_changed_payload, deferred=True)
        else:
            self._total_size = self._expanded_virtual_total_size(updated, offset_delta)
            self._configure_scrollbar()
            rows_changed_payload = list(self._rows)
            if not editing_bytes:
                self._emit_rows_changed(rows_changed_payload, deferred=True)
        self._render_offsets()
        if not incomplete_bytes_edit:
            target = self.instructions if editing_bytes else self.bytes
            values = [self._display_instruction(row.instruction) for row in self._rows] if editing_bytes else [self._display_bytes_row(row) for row in self._rows]
            self._set_editor_text(target, values)
            self._render_decoded_text()
            self._render_raw_instructions()
        if offset_delta or label_structure_changed or labels_changed or force_recalculation:
            self._refresh_jump_navigation()
            self._refresh_label_folding()
        if not self._virtual:
            self._scroll_static_document(self.scrollbar.value())
        coordinator = getattr(self, "_consistency_coordinator", None)
        if editing_bytes and coordinator is not None and coordinator.enabled():
            coordinator.accept_synchronous_rows(list(self._rows))
        # Reentrant row observers must see Assembly, offsets and the coordinator at
        # the same revision. Bytes edits intentionally do not trigger autosave.
        if editing_bytes and rows_changed_payload is not None:
            self._emit_rows_changed(rows_changed_payload)
        self._emit_selection_summary()
        source = self.bytes if editing_bytes else self.instructions
        self._remember_editor_text_signature(source)
        self._dirty_editor_kind = None

    def _offset_base_text(self) -> dict[str, str]:
        return {
            name: f"0x{base:08X}"
            for name, base in self._offset_bases().items()
        }

    def _set_editing_labels(
        self,
        labels: dict[str, str],
        block_range: tuple[int, int] | None = None,
    ) -> None:
        """Refresh label dependencies without rebuilding a resolver per line."""

        was_updating = self._updating
        self._updating = True
        self._labels = labels
        self._symbol_offsets = {name: [offset] for name, offset in labels.items()}
        cached = getattr(self, "_symbol_maps", None)
        if cached is None:
            cached = self._instruction_highlighter.symbol_maps(
                {}, self._variables, self._equates
            )
        maps = (
            {name.casefold(): value for name, value in labels.items()},
            cached[1],
            cached[2],
        )
        self._symbol_maps = maps
        self._symbol_resolver = MipsSymbolResolver.from_symbol_maps(maps)
        if block_range is None:
            self._instruction_highlighter.set_symbol_maps(maps)
            self._raw_instruction_highlighter.set_symbol_maps(maps)
        else:
            first, last = block_range
            self._instruction_highlighter.set_symbol_maps_for_blocks(
                maps,
                first,
                last,
            )
            self._raw_instruction_highlighter.set_symbol_maps_for_blocks(
                maps,
                first,
                last,
            )
        self.instructions.set_label_helpers(labels)
        self.instructions.update_jump_labels(labels)
        self._updating = was_updating

    def _byte_rows_from_lines(self, lines: list[str]) -> list[BinaryWorkbenchRowDTO] | None:
        rows: list[BinaryWorkbenchRowDTO] = []
        source_rows = self._aligned_byte_source_rows(lines)
        for index, line in enumerate(lines):
            source = source_rows[index]
            raw = "".join(line.split())
            if line.strip() == "-":
                rows.append(source)
                continue
            if not raw:
                rows.append(
                    BinaryWorkbenchRowDTO(
                        offsets=source.offsets,
                        instruction=self._bytes_fallback_instruction(source),
                        bytes_text="",
                    )
                )
                continue
            if len(raw) < ROW_BYTES * 2:
                rows.append(
                    BinaryWorkbenchRowDTO(
                        offsets=source.offsets,
                        instruction=self._bytes_fallback_instruction(source),
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
                rows.append(
                    BinaryWorkbenchRowDTO(
                        offsets=source.offsets,
                        instruction=source.instruction,
                        bytes_text=self._codec.bytes_text(chunk),
                    )
                )
        return self._rows_decoded_after_offset_rebuild(rows)

    def _aligned_byte_source_rows(
        self,
        lines: list[str],
    ) -> list[BinaryWorkbenchRowDTO]:
        previous = [self._display_bytes_row(row) for row in self._rows]
        indices = aligned_source_indices(
            previous,
            lines,
            self._active_bytes_alignment_hint,
        )
        return [
            self._rows[source]
            if source is not None and 0 <= source < len(self._rows)
            else BinaryWorkbenchRowDTO(offsets=self._offsets_for_row(index))
            for index, source in enumerate(indices)
        ]

    def _bytes_fallback_instruction(self, row: BinaryWorkbenchRowDTO) -> str:
        if annotation := preserved_source_annotation(row.instruction):
            return annotation
        return row.instruction if self._locked_virtual_bytes_edit() else ""

    def _previous_rows_for_bytes_preservation(
        self,
        updated: list[BinaryWorkbenchRowDTO],
    ) -> list[BinaryWorkbenchRowDTO]:
        previous_lines = [self._display_bytes_row(row) for row in self._rows]
        current_lines = [self._display_bytes_row(row) for row in updated]
        indices = aligned_source_indices(
            previous_lines,
            current_lines,
            self._active_bytes_alignment_hint,
        )
        return [
            self._rows[source]
            if source is not None and 0 <= source < len(self._rows)
            else current
            for source, current in zip(indices, updated)
        ]

    def _preserve_bytes_rows(
        self,
        updated: list[BinaryWorkbenchRowDTO],
    ) -> list[BinaryWorkbenchRowDTO]:
        return preserve_symbolic_rows(
            updated,
            self._previous_rows_for_bytes_preservation(updated),
            self._labels,
            self._variables,
            self._equates,
            self._codec,
            self._symbol_offsets,
        )

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
            decoded_instruction = editor_mips_instruction(raw_instruction, address)
            decoded.append(
                BinaryWorkbenchRowDTO(
                    offsets=row.offsets,
                    instruction=_preserve_comment(decoded_instruction, row.instruction),
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
        rows = self._reference_jump_rows(rows, lines, labels, variables, equates)
        rows = self._validated_standard_jump_rows(rows, lines)
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
        if (
            self._preserve_instruction_offsets()
            and not self._new_source_row_became_valid(lines)
        ):
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
        active_variables = self._variables if variables is None else variables
        active_equates = self._equates if equates is None else equates
        rows = build_source_line_rows(
            lines,
            self._columns or [BINARY_WORKBENCH_TEXT.FILE],
            self._offset_base_text(),
            self._codec,
            self._source_rows_start_offset(),
            labels,
            active_variables,
            active_equates,
            False,
        )
        rows = self._reference_jump_rows(rows, lines, labels, active_variables, active_equates)
        rows = self._validated_standard_jump_rows(rows, lines)
        rows = self._virtual_instruction_rows_with_previous_bytes(rows) if self._virtual else rows
        return self._rows_with_instruction_spacing(rows, lines)

    def _new_source_row_became_valid(self, lines: list[str]) -> bool:
        """Allow a newly inserted blank row to become code under locked shifting."""

        return any(
            index < len(self._rows)
            and self._rows[index].offsets.get(BINARY_WORKBENCH_TEXT.FILE) == "-"
            and not self._rows[index].bytes_text
            and byte_row_policy(
                self._rows[index].instruction,
                False,
            ).removable_from_bytes
            and bool(instruction_code(line))
            for index, line in enumerate(lines)
        )

    def _validated_standard_jump_rows(
        self,
        rows: list[BinaryWorkbenchRowDTO] | None,
        lines: list[str],
    ) -> list[BinaryWorkbenchRowDTO] | None:
        if rows is None:
            return None
        updated: list[BinaryWorkbenchRowDTO] = []
        for index, row in enumerate(rows):
            line = lines[index] if index < len(lines) else row.instruction
            if self._invalid_standard_jump_target(line):
                updated.append(
                    BinaryWorkbenchRowDTO(
                        row.offsets,
                        row.instruction,
                        "",
                        row.original_instruction,
                        row.original_bytes_text,
                    )
                )
                continue
            updated.append(row)
        return updated

    def _invalid_standard_jump_target(self, line: str) -> bool:
        code, _, _ = split_comment(line)
        match = STANDARD_JUMP_TARGET.search(code)
        if match is None:
            return False
        try:
            value = int(match.group("target"), 0)
        except ValueError:
            return False
        if value < JUMP_NAVIGATION_BASE:
            return True
        target = value - JUMP_NAVIGATION_BASE
        return target % ROW_BYTES != 0

    def _reference_jump_rows(
        self,
        rows: list[BinaryWorkbenchRowDTO] | None,
        lines: list[str],
        labels: dict[str, str] | None,
        variables: dict[str, str],
        equates: dict[str, str],
    ) -> list[BinaryWorkbenchRowDTO] | None:
        if rows is None or not self._jump_reference_offset:
            return rows
        symbols = self._reference_jump_symbols(labels or self._labels, variables, equates)
        updated: list[BinaryWorkbenchRowDTO] = []
        for index, row in enumerate(rows):
            line = lines[index] if index < len(lines) else row.instruction
            normalized = self._reference_jump_line(line, symbols)
            if normalized == line:
                updated.append(row)
                continue
            offset = self._reference_jump_row_offset(index)
            if offset is None:
                updated.append(row)
                continue
            replacement = build_source_line_rows(
                [normalized],
                self._columns or [BINARY_WORKBENCH_TEXT.FILE],
                self._offset_base_text(),
                self._codec,
                offset,
                labels,
                variables,
                equates,
                True,
            )
            if not replacement or not replacement[0].bytes_text:
                updated.append(row)
                continue
            encoded = replacement[0]
            updated.append(
                BinaryWorkbenchRowDTO(
                    row.offsets,
                    row.instruction,
                    encoded.bytes_text,
                    row.original_instruction,
                    row.original_bytes_text,
                )
            )
        return updated

    def _reference_jump_row_offset(self, index: int) -> int | None:
        try:
            return int(self._row_at(index).offsets.get(BINARY_WORKBENCH_TEXT.FILE, "-"), 16)
        except ValueError:
            return None

    def _reference_jump_line(self, line: str, symbols: dict[str, str]) -> str:
        def replacement(match: re.Match[str]) -> str:
            target = self._reference_jump_standard_target(match.group("target"), symbols)
            if target is None:
                return match.group(0)
            return f"{match.group('mnemonic')} 0x{target:08X}"

        return REFERENCE_JUMP_TARGET.sub(replacement, line)

    def _reference_jump_standard_target(self, token: str, symbols: dict[str, str]) -> int | None:
        if self._jump_reference_offset not in self._reference_offset_bases:
            return None
        value = self._reference_jump_value(token, symbols)
        if value is None:
            return None
        base = self._safe_reference_int(self._reference_offset_bases[self._jump_reference_offset])
        target = value - base
        if target < 0 or target % ROW_BYTES != 0:
            return None
        return target + JUMP_NAVIGATION_BASE

    def _reference_jump_value(self, token: str, symbols: dict[str, str]) -> int | None:
        normalized = token.lower()
        if normalized in symbols:
            return self._safe_reference_int(symbols[normalized])
        try:
            return int(token, 0)
        except ValueError:
            return None

    def _reference_jump_symbols(
        self,
        labels: dict[str, str],
        variables: dict[str, str],
        equates: dict[str, str],
    ) -> dict[str, str]:
        return {
            **{name.lower(): value for name, value in labels.items()},
            **{f"_{name.lstrip('_')}".lower(): value for name, value in variables.items()},
            **{f"@{name.lstrip('@')}".lower(): value for name, value in equates.items()},
        }

    def _safe_reference_int(self, value: str) -> int:
        try:
            return int(value, 0)
        except ValueError:
            return 0

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

    def _preserve_instruction_offsets(self) -> bool:
        if self._locked_virtual_instruction_edit():
            return True
        return not self._virtual and not self._edit_rules.allow_byte_shift

    def _source_rows_start_offset(self) -> int:
        return self._visible_start_offset if self._virtual else 0

    def _virtual_instruction_rows_with_previous_bytes(
        self,
        rows: list[BinaryWorkbenchRowDTO] | None,
    ) -> list[BinaryWorkbenchRowDTO] | None:
        if rows is None:
            return None
        if self._edit_rules.allow_byte_shift:
            return rows
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
        return (
            self.bytes.hasFocus()
            or bool(getattr(self.bytes, "_granular_editing", False))
            or bool(getattr(self.bytes, "_history_action_in_progress", False))
        )

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
        stripped = line.strip()
        if stripped == "-":
            return stripped
        raw = "".join(char for char in line if char in HEX_DIGITS)
        raw = raw[: ROW_BYTES * 2]
        raw = raw.upper() if self._uppercase_bytes else raw
        normalized = normalize_bytes_text(raw, self._group_bytes, False)
        group_width = self._group_bytes * 2
        if 0 < len(raw) < ROW_BYTES * 2 and len(raw) % group_width == 0:
            return f"{normalized} "
        return normalized

    def _normalized_instruction_lines(self) -> list[str]:
        text = self.instructions.toPlainText()
        normalized = normalize_instruction_text(text, self._uppercase_instructions)
        if normalized != text and not self._instructions_user_edit_in_progress():
            self._set_editor_text(self.instructions, normalized.split("\n"))
        return normalized.split("\n")


def _preserve_comment(instruction: str, previous_instruction: str) -> str:
    _, marker, comment = split_comment(previous_instruction)
    if not marker:
        return instruction
    suffix = f"{marker}{comment}"
    return f"{instruction} {suffix.lstrip()}"


def _without_spacing(text: str) -> str:
    return "".join(text.split())


def _has_incomplete_byte_rows(rows: list[BinaryWorkbenchRowDTO]) -> bool:
    return any(
        row.offsets.get(BINARY_WORKBENCH_TEXT.FILE) not in {None, "-"}
        and not row.bytes_text
        for row in rows
    )
