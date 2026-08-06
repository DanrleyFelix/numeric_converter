from __future__ import annotations

from dataclasses import replace
from types import MappingProxyType
from typing import Iterable, Mapping
from uuid import UUID

from src.core.binary_workbench.symbols.definitions.models import (
    SymbolDefinition,
    SymbolScope,
    display_symbol_name,
    normalize_symbol_name,
    stable_symbol_id,
    stable_symbol_id_from_normalized,
)


class SymbolRepository:
    """Maintain one copy-on-write local or global Symbol catalog."""

    def __init__(self, workspace_id: str, scope: SymbolScope, owner_tab_id: str | None = None) -> None:
        self.workspace_id = workspace_id
        self._namespace = UUID(workspace_id)
        self.scope = scope
        self.owner_tab_id = owner_tab_id
        self.revision = 0
        self._by_id: dict[str, SymbolDefinition] = {}
        self._by_name: dict[str, SymbolDefinition] = {}

    def definitions(self) -> tuple[SymbolDefinition, ...]:
        """Return definitions without exposing repository mutation."""

        return tuple(self._by_id.values())

    def by_name_view(self) -> Mapping[str, SymbolDefinition]:
        """Return an immutable lookup view without copying it."""

        return MappingProxyType(self._by_name)

    def resolve(self, name: object) -> SymbolDefinition | None:
        """Resolve one definition by normalized name."""

        return self._by_name.get(normalize_symbol_name(name))

    def replace_all(self, values: Mapping[str, str] | Iterable[SymbolDefinition]) -> None:
        """Replace a catalog while preserving matching identities."""

        if isinstance(values, Mapping):
            items, by_name = self._from_mapping(values)
        else:
            items = tuple(values)
            by_name = {item.normalized_name: item for item in items}
        by_id = {item.symbol_id: item for item in items}
        if by_id == self._by_id:
            return
        self.revision += 1
        self._by_id = by_id
        self._by_name = by_name

    def upsert(self, name: str, value: str, symbol_id: str | None = None) -> SymbolDefinition:
        """Insert or update one definition with copy-on-write maps."""

        key = normalize_symbol_name(name)
        current = self._by_name.get(key)
        identity = symbol_id or (
            current.symbol_id if current else stable_symbol_id(
                self._namespace, self.scope, name, self.owner_tab_id
            )
        )
        item = SymbolDefinition(
            identity, display_symbol_name(name), str(value), self.scope,
            self.owner_tab_id, self.revision + 1,
            (current.resolution_revision + 1) if current else 1,
        )
        by_id, by_name = dict(self._by_id), dict(self._by_name)
        if current is not None:
            by_id.pop(current.symbol_id, None)
        by_id[item.symbol_id], by_name[key] = item, item
        self.revision += 1
        self._by_id, self._by_name = by_id, by_name
        return item

    def remove(self, symbol_id: str) -> SymbolDefinition | None:
        """Remove one definition without scanning source tabs."""

        current = self._by_id.get(symbol_id)
        if current is None:
            return None
        by_id, by_name = dict(self._by_id), dict(self._by_name)
        by_id.pop(symbol_id, None)
        by_name.pop(current.normalized_name, None)
        self.revision += 1
        self._by_id, self._by_name = by_id, by_name
        return current

    def rename(self, symbol_id: str, name: str) -> SymbolDefinition:
        """Rename a definition while preserving its stable identity."""

        current = self._by_id[symbol_id]
        target = normalize_symbol_name(name)
        conflict = self._by_name.get(target)
        if conflict is not None and conflict.symbol_id != symbol_id:
            raise ValueError(f"Symbol '{name}' already exists.")
        updated = replace(
            current, name=display_symbol_name(name),
            catalog_revision=self.revision + 1,
            resolution_revision=current.resolution_revision + 1,
        )
        by_id, by_name = dict(self._by_id), dict(self._by_name)
        by_name.pop(current.normalized_name, None)
        by_id[symbol_id], by_name[target] = updated, updated
        self.revision += 1
        self._by_id, self._by_name = by_id, by_name
        return updated

    def _from_mapping(
        self,
        values: Mapping[str, str],
    ) -> tuple[tuple[SymbolDefinition, ...], dict[str, SymbolDefinition]]:
        """Canonicalize one legacy map without normalizing names repeatedly."""

        incoming: dict[str, tuple[str, str]] = {}
        for name, value in values.items():
            key = normalize_symbol_name(name)
            if key:
                incoming[key] = (display_symbol_name(name), str(value))
        removed = [item for key, item in self._by_name.items() if key not in incoming]
        added = [key for key in incoming if key not in self._by_name]
        inferred = (added[0], removed[0]) if len(added) == len(removed) == 1 else None
        items = tuple(
            _mapped_definition(self, key, name, value, inferred)
            for key, (name, value) in incoming.items()
        )
        return items, dict(zip(incoming, items))


def _mapped_definition(repository, key, name, value, inferred) -> SymbolDefinition:
    """Build one replacement item while retaining a matching or renamed ID."""

    current = repository._by_name.get(key)
    renamed = inferred[1] if inferred and inferred[0] == key else None
    identity = current or renamed
    return SymbolDefinition(
        identity.symbol_id if identity else stable_symbol_id_from_normalized(
            repository._namespace, repository.scope, key, repository.owner_tab_id
        ),
        name, value, repository.scope,
        repository.owner_tab_id, repository.revision + 1,
        identity.resolution_revision + (1 if renamed else 0) if identity else 0,
    )
