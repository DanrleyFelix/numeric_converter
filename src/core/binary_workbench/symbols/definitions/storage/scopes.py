from __future__ import annotations

from typing import Mapping

from src.core.binary_workbench.symbols.definitions.models import (
    SymbolDefinition,
    SymbolScope,
    normalize_symbol_name,
)
from src.core.binary_workbench.symbols.definitions.storage.base import SymbolRepository


class SymbolRepositorySnapshot:
    """Expose a shared immutable Local-before-Global resolver."""

    def __init__(
        self,
        local_by_name: Mapping[str, SymbolDefinition],
        global_by_name: Mapping[str, SymbolDefinition],
        catalog_revision: int,
    ) -> None:
        self.local_by_name = local_by_name
        self.global_by_name = global_by_name
        self.catalog_revision = catalog_revision

    def resolve(self, name: object) -> SymbolDefinition | None:
        """Resolve with Local-before-Global precedence in constant time."""

        key = normalize_symbol_name(name)
        return self.local_by_name.get(key) or self.global_by_name.get(key)


class GlobalSymbolRepository(SymbolRepository):
    """Store shared definitions without tab occurrences."""

    def __init__(self, workspace_id: str) -> None:
        super().__init__(workspace_id, SymbolScope.GLOBAL)


class LocalSymbolRepository:
    """Materialize local repositories only for requested tabs."""

    def __init__(self, workspace_id: str) -> None:
        self.workspace_id = workspace_id
        self._tabs: dict[str, SymbolRepository] = {}

    def for_tab(self, tab_id: str) -> SymbolRepository:
        """Return or lazily create one tab-owned repository."""

        if tab_id not in self._tabs:
            self._tabs[tab_id] = SymbolRepository(
                self.workspace_id, SymbolScope.LOCAL, tab_id
            )
        return self._tabs[tab_id]

    def is_materialized(self, tab_id: str) -> bool:
        """Report whether local definitions for a tab were requested."""

        return tab_id in self._tabs


class SymbolQueryService:
    """Create lightweight resolver snapshots for materialized tabs."""

    def __init__(
        self,
        global_repository: GlobalSymbolRepository,
        local_repository: LocalSymbolRepository,
    ) -> None:
        self._global = global_repository
        self._local = local_repository

    def snapshot(self, tab_id: str) -> SymbolRepositorySnapshot:
        """Share repository maps without copying thousands of definitions."""

        local = self._local.for_tab(tab_id)
        return SymbolRepositorySnapshot(
            local.by_name_view(),
            self._global.by_name_view(),
            (self._global.revision << 32) | local.revision,
        )
