from __future__ import annotations

from src.core.binary_workbench.byte_editing import ByteEditViolation
from src.core.binary_workbench.mips_r3000a import editor_mips_instruction
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO


class GridBytesStructuralEditingMixin:
    """Apply Bytes-origin row splices without rebuilding the whole editor."""

    def _setup_bytes_structural_editing(self) -> None:
        self._removed_bytes_rows: list[
            tuple[int, tuple[BinaryWorkbenchRowDTO, ...]]
        ] = []

    def _remember_removed_bytes_rows(
        self,
        first: int,
        rows: tuple[BinaryWorkbenchRowDTO, ...],
    ) -> None:
        self._removed_bytes_rows.append((first, rows))
        del self._removed_bytes_rows[:-32]

    def _try_bytes_structure_update(self, lines: list[str]) -> bool:
        """Reconcile one native Bytes document splice incrementally."""

        delta = len(lines) - len(self._rows)
        if not delta:
            return False
        previous = [self._display_bytes_row(row) for row in self._rows]
        first = _common_prefix(previous, lines)
        hint = self._active_bytes_alignment_hint
        if hint is not None:
            first = min(max(0, hint), min(len(previous), len(lines)))
        suffix = _common_suffix(previous, lines, first)
        removed = max(0, len(previous) - first - suffix)
        inserted_lines = lines[first : len(lines) - suffix if suffix else len(lines)]
        if len(inserted_lines) - removed != delta:
            return False
        if (
            delta > 0
            and hint is None
            and first == len(previous)
            and all(not _canonical_bytes(line) for line in inserted_lines)
        ):
            return False
        if removed:
            removed_rows = tuple(self._rows[first : first + removed])
            violation = self._byte_row_removal_violation(
                tuple(range(first, first + removed))
            )
            if violation is not ByteEditViolation.NONE:
                return False
            self._remember_removed_bytes_rows(first, removed_rows)
        inserted = self._rows_for_bytes_insertion(first, inserted_lines)
        if inserted is None:
            return False
        coordinator = getattr(self, "_consistency_coordinator", None)
        if coordinator is None or not coordinator.enabled():
            return False
        coordinator.accept_bytes_structure_splice(first, removed, inserted)
        incomplete = any(
            0 < len(_canonical_bytes(line)) < ROW_BYTES * 2
            for line in inserted_lines
        )
        self._bytes_staged_incomplete = incomplete
        self._bytes_staged_block = first if incomplete else None
        self._remember_editor_text_signature(self.bytes)
        self._dirty_editor_kind = None
        return True

    def _try_bytes_structural_history_update(self) -> bool:
        """Replay a known row Undo/Redo without scanning every Bytes block.

        Structural Bytes commands already carry their source-row boundary and
        removed-row cache.  Falling back to prefix/suffix matching here made a
        single Undo proportional to files with thousands of instructions.
        """

        if not bool(getattr(self.bytes, "_history_action_in_progress", False)):
            return False
        first = self._active_bytes_alignment_hint
        delta = self.bytes.document().blockCount() - len(self._rows)
        if not delta:
            return False
        if first is None:
            first = self._cached_history_splice_start(delta)
        if first is None:
            return False
        first = min(max(0, first), len(self._rows))
        removed = max(0, -delta)
        inserted: list[BinaryWorkbenchRowDTO] = []
        if delta > 0:
            lines: list[str] = []
            for index in range(first, first + delta):
                block = self.bytes.document().findBlockByNumber(index)
                if not block.isValid():
                    return False
                lines.append(self._normalized_bytes_line(block.text()))
            restored = self._rows_for_bytes_insertion(first, lines)
            if restored is None:
                return False
            inserted = restored
        elif first + removed > len(self._rows):
            return False
        coordinator = getattr(self, "_consistency_coordinator", None)
        if coordinator is None or not coordinator.enabled():
            return False
        coordinator.accept_bytes_structure_splice(first, removed, inserted)
        self._bytes_staged_incomplete = False
        self._bytes_staged_block = None
        self._remember_editor_text_signature(self.bytes)
        self._dirty_editor_kind = None
        return True

    def _cached_history_splice_start(self, delta: int) -> int | None:
        """Locate a structural Bytes Undo from its bounded removal journal."""

        expected = abs(delta)
        for first, rows in reversed(self._removed_bytes_rows):
            if len(rows) != expected:
                continue
            # The first Undo restores the structurally deleted *empty* row;
            # later Undo commands restore its bytes nibble by nibble.  The
            # journal therefore supplies the boundary even when the restored
            # text does not yet match the previously assembled row.
            return first
        return None

    def _rows_for_bytes_insertion(
        self,
        first: int,
        lines: list[str],
    ) -> list[BinaryWorkbenchRowDTO] | None:
        cached = self._cached_removed_rows(first, lines)
        if cached is not None:
            return list(cached)
        address = self._source_offset_before_row(first)
        rows: list[BinaryWorkbenchRowDTO] = []
        for line in lines:
            raw = _canonical_bytes(line)
            if not raw:
                rows.append(BinaryWorkbenchRowDTO({}, "", ""))
                continue
            if len(raw) < ROW_BYTES * 2:
                if not _is_hex(raw):
                    return None
                rows.append(BinaryWorkbenchRowDTO({}, "", ""))
                continue
            if len(raw) != ROW_BYTES * 2 or not _is_hex(raw):
                return None
            data = bytes.fromhex(raw)
            instruction = editor_mips_instruction(
                self._codec.disassemble(data, address),
                address,
            )
            rows.append(BinaryWorkbenchRowDTO({}, instruction, self._codec.bytes_text(data)))
            address += ROW_BYTES
        return rows

    def _cached_removed_rows(
        self,
        first: int,
        lines: list[str],
    ) -> tuple[BinaryWorkbenchRowDTO, ...] | None:
        for cached_first, rows in reversed(self._removed_bytes_rows):
            if cached_first != first or len(rows) != len(lines):
                continue
            if all(
                _line_matches_cached(line, self._display_bytes_row(row))
                for line, row in zip(lines, rows)
            ):
                return rows
        return None


def _common_prefix(previous: list[str], current: list[str]) -> int:
    limit = min(len(previous), len(current))
    index = 0
    while index < limit and previous[index] == current[index]:
        index += 1
    return index


def _common_suffix(previous: list[str], current: list[str], first: int) -> int:
    limit = min(len(previous), len(current)) - first
    index = 0
    while index < limit and previous[-1 - index] == current[-1 - index]:
        index += 1
    return index


def _canonical_bytes(value: str) -> str:
    return "".join(value.split()).upper()


def _is_hex(value: str) -> bool:
    return all(character in "0123456789ABCDEF" for character in value)


def _line_matches_cached(line: str, cached: str) -> bool:
    current = _canonical_bytes(line)
    expected = _canonical_bytes(cached)
    return current == expected
