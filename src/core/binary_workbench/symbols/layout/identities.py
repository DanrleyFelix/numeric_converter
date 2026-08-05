from __future__ import annotations

class InstructionIdentityJournal:
    """Preserve instruction IDs across splice, undo, and redo operations."""

    def __init__(self, workspace_id: str, tab_id: str, count: int = 0) -> None:
        self._workspace_id = workspace_id
        self._tab_id = tab_id
        self._next = 0
        self._ids: list[str] = []
        self._tombstones: list[tuple[int, tuple[str, ...]]] = []
        self.splice(0, 0, count)

    @property
    def ids(self) -> tuple[str, ...]:
        """Return stable IDs in current source order."""

        return tuple(self._ids)

    def splice(self, first: int, removed: int, inserted: int) -> tuple[str, ...]:
        """Replace an ID range and journal removed identities."""

        start = min(max(0, first), len(self._ids))
        end = min(len(self._ids), start + max(0, removed))
        deleted = tuple(self._ids[start:end])
        if deleted:
            self._tombstones.append((start, deleted))
        created = tuple(self._new_id() for _ in range(max(0, inserted)))
        self._ids[start:end] = created
        return created

    def restore_last(self) -> bool:
        """Restore the most recently removed identity range."""

        if not self._tombstones:
            return False
        first, values = self._tombstones.pop()
        self._ids[first:first] = values
        return True

    def _new_id(self) -> str:
        value = f"{self._tab_id}:{self._next:x}"
        self._next += 1
        return value
