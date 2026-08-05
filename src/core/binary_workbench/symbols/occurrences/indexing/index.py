from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from src.core.binary_workbench.symbols.definitions import SymbolRepositorySnapshot
from src.core.binary_workbench.symbols.occurrences.indexing.storage import (
    SYMBOL_TOKEN, PackedOccurrence, StoredOccurrence, materialize,
    occurrences, slot, stored_ids,
)
from src.core.binary_workbench.symbols.occurrences.models import (
    ReferenceDiff, SymbolOccurrence,
)


class SymbolOccurrenceIndex:
    """Index source references by instruction, Symbol, and occurrence ID."""

    def __init__(self, tab_id: str) -> None:
        self.tab_id = tab_id
        self.revision = 0
        self._by_instruction: dict[str, str | tuple[str, ...]] = {}
        self._by_symbol: dict[str, list[str]] = defaultdict(list)
        self._by_id: dict[str, StoredOccurrence] = {}

    def occurrences_for_instruction(self, instruction_id: str) -> tuple[SymbolOccurrence, ...]:
        """Return references used by one stable instruction."""

        stored = self._by_instruction.get(instruction_id)
        if stored is None:
            value = self._by_id.get(instruction_id)
            return () if value is None else (
                materialize(self.tab_id, instruction_id, value),
            )
        ids = (stored,) if isinstance(stored, str) else stored
        return tuple(
            materialize(self.tab_id, item, self._by_id[item])
            for item in ids if item in self._by_id
        )

    def occurrences_for_symbol(self, symbol_id: str) -> tuple[SymbolOccurrence, ...]:
        """Return only known occurrences of one selected Symbol."""

        return tuple(
            materialize(self.tab_id, item, self._by_id[item])
            for item in self._by_symbol.get(symbol_id, ()) if item in self._by_id
        )

    def replace_instruction_references(
        self, instruction_id: str, text: str,
        resolver: SymbolRepositorySnapshot,
    ) -> ReferenceDiff:
        """Tokenize one line and atomically replace its references."""

        previous = self.occurrences_for_instruction(instruction_id)
        current = tuple(occurrences(self.tab_id, instruction_id, text, resolver))
        old, new = ({slot(item): item for item in values} for values in (previous, current))
        retained = tuple(item for key, item in new.items() if old.get(key) == item)
        changed = tuple(
            (old[key], item) for key, item in new.items()
            if key in old and old[key] != item
        )
        removed = tuple(item for key, item in old.items() if key not in new)
        added = tuple(item for key, item in new.items() if key not in old)
        if previous == current:
            return ReferenceDiff(retained=retained)
        self._discard(previous)
        self._store(current)
        self._by_instruction.pop(instruction_id, None)
        if len(current) > 1:
            self._by_instruction[instruction_id] = stored_ids(current)
        self.revision += 1
        return ReferenceDiff(added, removed, retained, changed)

    def rebuild(
        self, instructions: Iterable[tuple[str, str]],
        resolver: SymbolRepositorySnapshot,
    ) -> None:
        """Build one tab index in linear time over source tokens."""

        symbol_ids = {name: item.symbol_id for name, item in resolver.global_by_name.items()}
        symbol_ids.update((name, item.symbol_id) for name, item in resolver.local_by_name.items())
        by_instruction: dict[str, str | tuple[str, ...]] = {}
        by_symbol: dict[str, list[str]] = defaultdict(list)
        by_id: dict[str, StoredOccurrence] = {}
        for instruction_id, text in instructions:
            first_id: str | None = None
            extras: list[str] | None = None
            for operand_index, match in enumerate(SYMBOL_TOKEN.finditer(text)):
                symbol_id = symbol_ids.get(match.group(2))
                if symbol_id is None:
                    symbol_id = symbol_ids.get(match.group(2).casefold())
                if symbol_id is None:
                    continue
                occurrence_id = instruction_id if first_id is None else f"{instruction_id}:{operand_index}"
                by_symbol[symbol_id].append(occurrence_id)
                by_id[occurrence_id] = _packed(
                    symbol_id, instruction_id, operand_index, match, first_id is None
                )
                if first_id is None:
                    first_id = occurrence_id
                else:
                    extras = [first_id] if extras is None else extras
                    extras.append(occurrence_id)
            if extras is not None:
                by_instruction[instruction_id] = tuple(extras)
        self._by_instruction, self._by_symbol, self._by_id = by_instruction, by_symbol, by_id
        self.revision += 1

    def _discard(self, values: Iterable[SymbolOccurrence]) -> None:
        """Remove a small instruction-owned occurrence set."""

        for item in values:
            self._by_id.pop(item.occurrence_id, None)
            stored = self._by_symbol.get(item.symbol_id)
            if stored is not None and item.occurrence_id in stored:
                stored.remove(item.occurrence_id)
                if not stored:
                    self._by_symbol.pop(item.symbol_id, None)

    def _store(self, values: Iterable[SymbolOccurrence]) -> None:
        """Store a small instruction-owned occurrence set."""

        for item in values:
            self._by_id[item.occurrence_id] = item
            self._by_symbol[item.symbol_id].append(item.occurrence_id)


def _packed(symbol_id, instruction_id, operand_index, match, first) -> PackedOccurrence:
    """Pack rebuild data without allocating public occurrence objects."""

    tail = (operand_index, match.start(), len(match.group(0)), match.group(1))
    return (symbol_id, *tail) if first else (symbol_id, instruction_id, *tail)
