from __future__ import annotations


class RangeConsistencyIndex:
    """Track which projected rows are current without parsing source text."""

    def __init__(self) -> None:
        self.revision = 0
        self._current = bytearray()

    def reset(self, count: int, revision: int) -> None:
        """Mark a newly loaded projection as fully current."""

        self.revision = revision
        self._current = bytearray([1]) * max(0, count)

    def invalidate_from(self, first: int, count: int, revision: int) -> None:
        """Preserve the valid prefix and invalidate only the shifted suffix."""

        prefix = min(max(0, first), count, len(self._current))
        self.revision = revision
        self._current = self._current[:prefix] + bytearray(max(0, count - prefix))

    def mark(self, indices: tuple[int, ...], revision: int) -> None:
        """Mark one committed batch current for the active revision."""

        if revision != self.revision:
            return
        for index in indices:
            if 0 <= index < len(self._current):
                self._current[index] = 1

    def is_current(self, first: int, last: int, revision: int) -> bool:
        """Return true when a requested inclusive range needs zero work."""

        if revision != self.revision or not self._current:
            return False
        start = min(max(0, first), len(self._current))
        end = min(max(start, last + 1), len(self._current))
        return start == end or all(self._current[start:end])
