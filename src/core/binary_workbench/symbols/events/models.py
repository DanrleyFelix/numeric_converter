from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SymbolEvent:
    """Base metadata shared by aggregated Core symbol events."""

    tab_id: str | None
    version_id: str | None
    catalog_revision: int
    source_revision: int = 0


@dataclass(frozen=True, slots=True)
class SymbolDefinitionsChanged(SymbolEvent):
    """Report one committed definition transaction."""

    symbol_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class InstructionReferencesReplaced(SymbolEvent):
    """Report one committed reference replacement."""

    instruction_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OffsetLayoutInvalidated(SymbolEvent):
    """Report the first structurally affected instruction."""

    first_instruction_id: str | None = None


@dataclass(frozen=True, slots=True)
class ViewportRequested(SymbolEvent):
    """Request projection of a visible instruction interval."""

    first: int = 0
    last: int = 0
    viewport_epoch: int = 0


@dataclass(frozen=True, slots=True)
class TabActivated(SymbolEvent):
    """Report activation without materializing unrelated tabs."""

    activation_epoch: int = 0


@dataclass(frozen=True, slots=True)
class ConsistencyBarrierRequested(SymbolEvent):
    """Request an atomic active-owner consistency barrier."""

    reason: str = ""
