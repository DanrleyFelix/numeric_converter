from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DebuggerMemoryZone:
    """Describe one import region inside the virtual memory image."""

    start: int
    end: int
    origin: str
    status: str
    loaded_bytes: int

    @property
    def size(self) -> int:
        """Return the inclusive zone size."""

        return self.end - self.start + 1


@dataclass(frozen=True)
class DebuggerMemoryOverlap:
    """Describe one real overlap between two ordered imports."""

    first_origin: str
    second_origin: str
    start: int
    end: int

    @property
    def size(self) -> int:
        """Return the number of bytes overwritten by the later import."""

        return self.end - self.start + 1


@dataclass(frozen=True)
class DebuggerMemoryImage:
    """Hold a complete immutable initial debugger memory configuration."""

    start: int
    end: int
    data: bytes
    initial_snapshot: bytes
    zones: tuple[DebuggerMemoryZone, ...]
    overlaps: tuple[DebuggerMemoryOverlap, ...]
    stack_start: int | None
    stack_end: int | None
    initial_registers: dict[str, int]
    initial_pc: int
    ignored_addresses: frozenset[int]

    @property
    def size(self) -> int:
        """Return the inclusive virtual memory image size."""

        return self.end - self.start + 1

    def contains(self, address: int, size: int = 1) -> bool:
        """Return whether a complete interval belongs to the image."""

        if size < 0:
            return False
        interval_end = address + size - 1
        in_image = self.start <= address and interval_end <= self.end
        in_stack = (
            self.stack_start is not None
            and self.stack_end is not None
            and self.stack_start <= address
            and interval_end <= self.stack_end
        )
        return in_image or in_stack

    @property
    def ranges(self) -> tuple[tuple[int, int], ...]:
        """Return declared and automatic stack ranges mapped by the backend."""

        ranges = [(self.start, self.end)]
        if self.stack_start is not None and self.stack_end is not None:
            ranges.append((self.stack_start, self.stack_end))
        return tuple(ranges)

    def row_ranges(self, row_size: int) -> tuple[tuple[int, int], ...]:
        """Return merged mapped ranges aligned to complete display rows."""

        if row_size <= 0:
            raise ValueError("Row size must be positive.")
        aligned = sorted(
            (
                start - start % row_size,
                end - end % row_size,
            )
            for start, end in self.ranges
        )
        merged: list[tuple[int, int]] = []
        for start, end in aligned:
            if merged and start <= merged[-1][1] + row_size:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        return tuple(merged)

    def row_count(self, row_size: int) -> int:
        """Return the number of aligned rows across every mapped range."""

        return sum(
            ((end - start) // row_size) + 1
            for start, end in self.row_ranges(row_size)
        )

    def row_address(self, row: int, row_size: int) -> int | None:
        """Resolve one virtual display row to its mapped start address."""

        remaining = row
        for start, end in self.row_ranges(row_size):
            count = ((end - start) // row_size) + 1
            if 0 <= remaining < count:
                return start + remaining * row_size
            remaining -= count
        return None

    def row_index(self, address: int, row_size: int) -> int | None:
        """Resolve one mapped address to its concatenated display row."""

        aligned = address - address % row_size
        consumed = 0
        for start, end in self.row_ranges(row_size):
            if start <= aligned <= end:
                return consumed + ((aligned - start) // row_size)
            consumed += ((end - start) // row_size) + 1
        return None
