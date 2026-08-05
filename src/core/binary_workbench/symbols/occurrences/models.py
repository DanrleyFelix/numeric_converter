from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SymbolOccurrence:
    """Bind one source token to a stable instruction and symbol identity."""

    occurrence_id: str
    symbol_id: str
    tab_id: str
    instruction_id: str
    operand_index: int
    token_start: int
    token_length: int
    source_sigil: str


@dataclass(frozen=True, slots=True)
class ReferenceDiff:
    """Describe an atomic replacement of one instruction's references."""

    added: tuple[SymbolOccurrence, ...] = ()
    removed: tuple[SymbolOccurrence, ...] = ()
    retained: tuple[SymbolOccurrence, ...] = ()
    changed: tuple[tuple[SymbolOccurrence, SymbolOccurrence], ...] = ()
