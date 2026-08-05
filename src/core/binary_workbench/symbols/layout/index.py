from __future__ import annotations

from collections.abc import Iterable

from src.core.binary_workbench.symbols.occurrences import SymbolOccurrenceIndex
from src.core.binary_workbench.symbols.layout.tracking import SequentialPositionTracker

LAYOUT_BLOCK_SIZE = 256


class InstructionLayoutIndex:
    """Resolve instruction offsets using 256-entry blocks and prefix sums."""

    def __init__(
        self,
        instruction_ids: Iterable[str] = (),
        sizes: Iterable[int] = (),
        base: int = 0,
        sequential_id_prefix: str | None = None,
        sequential_id_base: int = 16,
    ) -> None:
        self.base = base
        self.layout_revision = 0
        self.resolved_layout_revision = 0
        self.dirty_from_instruction: str | None = None
        self._ids = list(instruction_ids)
        self._sizes = [max(0, int(value)) for value in sizes]
        if len(self._ids) != len(self._sizes):
            raise ValueError("Instruction IDs and sizes must have equal lengths.")
        self._sequential_id_prefix = sequential_id_prefix
        self._sequential_id_base = sequential_id_base
        self._sequential_positions = (
            SequentialPositionTracker(len(self._ids))
            if sequential_id_prefix is not None else None
        )
        self._rebuild(build_positions=sequential_id_prefix is None)

    def set_base(self, base: int) -> None:
        """Change the first offset in constant time."""

        if self.base == base:
            return
        self.base = base
        self.layout_revision += 1

    def append(self, instruction_id: str, size: int) -> int | None:
        """Append the last instruction and return its immediate offset."""

        offset = self.base + self.total_bytes
        position = len(self._ids)
        self._ids.append(instruction_id)
        self._sizes.append(max(0, size))
        block = (len(self._sizes) - 1) // LAYOUT_BLOCK_SIZE
        if block == len(self._block_sums):
            self._block_sums.append(0)
        self._block_sums[block] += max(0, size)
        if self._positions is not None:
            self._positions[instruction_id] = len(self._ids) - 1
        elif self._sequential_positions is not None:
            self._sequential_positions.remember(instruction_id, position)
        self._rebuild_fenwick()
        self.layout_revision += 1
        return offset if size > 0 else None

    def splice(
        self,
        first: int,
        removed: int,
        inserted: Iterable[tuple[str, int]],
    ) -> None:
        """Apply one aggregated structural edit and rebuild block metadata."""

        start = min(max(0, first), len(self._ids))
        end = min(len(self._ids), start + max(0, removed))
        values = tuple(inserted)
        if start < len(self._ids):
            self.dirty_from_instruction = self._ids[start]
        elif values:
            self.dirty_from_instruction = values[0][0]
        self._ids[start:end] = [item[0] for item in values]
        self._sizes[start:end] = [max(0, item[1]) for item in values]
        sequential = self._sequential_id_prefix is not None
        if sequential:
            self._sequential_positions.splice(start, end, values)
        self._rebuild(build_positions=not sequential)
        self.layout_revision += 1

    def offset_for(self, instruction_id: str) -> int | None:
        """Return the current offset without materializing offset strings."""

        position = self._position_for(instruction_id)
        if position is None or self._sizes[position] <= 0:
            return None
        block, local = divmod(position, LAYOUT_BLOCK_SIZE)
        return self.base + self._prefix_blocks(block) + sum(
            self._sizes[block * LAYOUT_BLOCK_SIZE:block * LAYOUT_BLOCK_SIZE + local]
        )

    def offsets_for(
        self,
        symbol_id: str,
        occurrences: SymbolOccurrenceIndex,
    ) -> tuple[int, ...]:
        """Resolve offsets only for occurrences of one selected symbol."""

        return tuple(
            offset
            for item in occurrences.occurrences_for_symbol(symbol_id)
            if (offset := self.offset_for(item.instruction_id)) is not None
        )

    @property
    def total_bytes(self) -> int:
        """Return emitted bytes in logarithmic time."""

        return self._prefix_blocks(len(self._block_sums))

    def _rebuild(self, build_positions: bool = True) -> None:
        self._positions = (
            {value: index for index, value in enumerate(self._ids)}
            if build_positions
            else None
        )
        self._block_sums = [
            sum(self._sizes[start:start + LAYOUT_BLOCK_SIZE])
            for start in range(0, len(self._sizes), LAYOUT_BLOCK_SIZE)
        ]
        self._rebuild_fenwick()

    def _position_for(self, instruction_id: str) -> int | None:
        if self._positions is not None:
            return self._positions.get(instruction_id)
        if self._sequential_positions is None or self._sequential_id_prefix is None:
            return None
        return self._sequential_positions.position(
            instruction_id,
            self._sequential_id_prefix,
            self._sequential_id_base,
            len(self._ids),
        )

    def _rebuild_fenwick(self) -> None:
        self._fenwick = [0] * (len(self._block_sums) + 1)
        for index, value in enumerate(self._block_sums, 1):
            cursor = index
            while cursor < len(self._fenwick):
                self._fenwick[cursor] += value
                cursor += cursor & -cursor

    def _prefix_blocks(self, count: int) -> int:
        total = 0
        cursor = min(count, len(self._block_sums))
        while cursor:
            total += self._fenwick[cursor]
            cursor -= cursor & -cursor
        return total
