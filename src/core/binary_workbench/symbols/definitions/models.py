from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID, uuid5


class SymbolScope(str, Enum):
    """Identify whether a symbol is shared or owned by one tab."""

    GLOBAL = "global"
    LOCAL = "local"


class ProcessingClass(str, Enum):
    """Classify work so extraordinary processing is always explicit."""

    ORDINARY = "ordinary"
    EXTRAORDINARY = "extraordinary"


@dataclass(frozen=True, slots=True)
class SymbolDefinition:
    """Represent one canonical local or global symbol definition."""

    symbol_id: str
    name: str
    value: str
    scope: SymbolScope
    owner_tab_id: str | None = None
    catalog_revision: int = 0
    resolution_revision: int = 0

    @property
    def normalized_name(self) -> str:
        """Return the case-insensitive lookup key without syntax aliases."""

        return normalize_symbol_name(self.name)


def normalize_symbol_name(name: object) -> str:
    """Normalize ``_`` and ``@`` aliases to one case-insensitive name."""

    return str(name).strip().lstrip("_@").casefold()


def display_symbol_name(name: object) -> str:
    """Return a persisted symbol name without a source sigil."""

    return str(name).strip().lstrip("_@")


def stable_symbol_id(
    workspace_id: str | UUID,
    scope: SymbolScope,
    name: object,
    owner_tab_id: str | None = None,
) -> str:
    """Build a deterministic symbol ID for legacy payload migration."""

    namespace = workspace_id if isinstance(workspace_id, UUID) else UUID(workspace_id)
    normalized = normalize_symbol_name(name)
    identity = (
        f"global:{normalized}"
        if scope is SymbolScope.GLOBAL
        else f"local:{owner_tab_id or ''}:{normalized}"
    )
    return str(uuid5(namespace, identity))
