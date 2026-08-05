from __future__ import annotations

import re
from collections.abc import Iterable

from src.core.binary_workbench.symbols.definitions import SymbolRepositorySnapshot
from src.core.binary_workbench.symbols.occurrences.models import SymbolOccurrence

SYMBOL_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_])([_@])([A-Za-z_][A-Za-z0-9_]*)(?![A-Za-z0-9_])"
)
PackedOccurrence = (
    tuple[str, int, int, int, str]
    | tuple[str, str, int, int, int, str]
)
StoredOccurrence = SymbolOccurrence | PackedOccurrence


def occurrences(
    tab_id: str,
    instruction_id: str,
    text: str,
    resolver: SymbolRepositorySnapshot,
) -> Iterable[SymbolOccurrence]:
    """Resolve all Symbol tokens from one source instruction."""

    found = 0
    for operand_index, match in enumerate(SYMBOL_TOKEN.finditer(text)):
        definition = resolver.resolve(match.group(2))
        if definition is None:
            continue
        yield SymbolOccurrence(
            instruction_id if found == 0 else f"{instruction_id}:{operand_index}",
            definition.symbol_id, tab_id, instruction_id, operand_index,
            match.start(), len(match.group(0)), match.group(1),
        )
        found += 1


def slot(item: SymbolOccurrence) -> tuple[int, int]:
    """Return the stable operand slot used by incremental diffs."""

    return item.operand_index, item.token_start


def stored_ids(values: tuple[SymbolOccurrence, ...]) -> str | tuple[str, ...]:
    """Compact the common single-occurrence instruction case."""

    return (
        values[0].occurrence_id if len(values) == 1
        else tuple(item.occurrence_id for item in values)
    )


def materialize(
    tab_id: str,
    occurrence_id: str,
    value: StoredOccurrence,
) -> SymbolOccurrence:
    """Create the public occurrence object only when requested."""

    if isinstance(value, SymbolOccurrence):
        return value
    if len(value) == 5:
        symbol_id, operand_index, start, length, sigil = value
        instruction_id = occurrence_id
    else:
        symbol_id, instruction_id, operand_index, start, length, sigil = value
    return SymbolOccurrence(
        occurrence_id, symbol_id, tab_id, instruction_id,
        operand_index, start, length, sigil,
    )
