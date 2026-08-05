from __future__ import annotations


class SequentialPositionTracker:
    """Translate stable sequential IDs through aggregated source splices."""

    def __init__(self, initial_count: int) -> None:
        self.initial_count = initial_count
        self._edits: list[tuple[int, int, int]] = []
        self._inserted: dict[str, tuple[int, int]] = {}

    def splice(
        self,
        start: int,
        end: int,
        inserted: tuple[tuple[str, int], ...],
    ) -> None:
        """Record one positional transform without rebuilding all IDs."""

        self._edits.append((start, end, len(inserted) - (end - start)))
        epoch = len(self._edits)
        self._inserted.update(
            (instruction_id, (start + index, epoch))
            for index, (instruction_id, _size) in enumerate(inserted)
        )

    def remember(self, instruction_id: str, position: int) -> None:
        """Register an appended stable ID at the current edit epoch."""

        self._inserted[instruction_id] = (position, len(self._edits))

    def position(
        self,
        instruction_id: str,
        prefix: str,
        number_base: int,
        current_count: int,
    ) -> int | None:
        """Resolve one ID by replaying only structural transforms."""

        inserted = self._inserted.get(instruction_id)
        if inserted is not None:
            position, epoch = inserted
        else:
            if not instruction_id.startswith(prefix):
                return None
            try:
                position = int(instruction_id[len(prefix):], number_base)
            except ValueError:
                return None
            if position >= self.initial_count:
                return None
            epoch = 0
        for start, end, delta in self._edits[epoch:]:
            if position < start:
                continue
            if position < end:
                return None
            position += delta
        return position if 0 <= position < current_count else None
