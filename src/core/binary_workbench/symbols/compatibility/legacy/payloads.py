from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass

from src.core.binary_workbench.symbol_values import merged_symbol_values
from src.core.binary_workbench.symbols.definitions import (
    SymbolDefinition,
    SymbolScope,
    display_symbol_name,
    stable_symbol_id,
)


@dataclass(frozen=True, slots=True)
class AdaptedSymbols:
    """Return canonical definitions and compatibility conflicts."""

    definitions: tuple[SymbolDefinition, ...]
    legacy_detected: bool
    conflicts: tuple[str, ...] = ()


class LegacySymbolsPayloadAdapter:
    """Convert modern or legacy maps into one Symbol collection."""

    def __init__(self, workspace_id: str) -> None:
        self.workspace_id = workspace_id

    def adapt(
        self,
        payload: Mapping[str, object],
        scope: SymbolScope,
        owner_tab_id: str | None = None,
        modern_key: str = "symbol_definitions",
    ) -> AdaptedSymbols:
        """Read definitions first and legacy maps only as compatibility input."""

        modern = payload.get(modern_key)
        if isinstance(modern, list):
            definitions = tuple(
                item for raw in modern
                if (item := _definition(raw, scope, owner_tab_id)) is not None
            )
            conflicts = _modern_conflicts(
                payload, scope, modern_key, modern, definitions
            )
            return AdaptedSymbols(definitions, False, conflicts)
        symbols = _string_map(payload.get(
            "global_symbols" if scope is SymbolScope.GLOBAL else "symbols"
        ))
        values = merged_symbol_values(
            symbols,
            _string_map(payload.get("variables")),
            _string_map(payload.get("equates")),
        )
        keys = (
            "global_symbols" if scope is SymbolScope.GLOBAL else "symbols",
            "variables",
            "equates",
        )
        return AdaptedSymbols(
            tuple(self.from_mapping(values, scope, owner_tab_id)),
            any(key in payload for key in keys),
        )

    def from_mapping(
        self,
        values: Mapping[str, str],
        scope: SymbolScope,
        owner_tab_id: str | None = None,
    ) -> Iterator[SymbolDefinition]:
        """Generate deterministic definitions from canonical legacy values."""

        for name, value in values.items():
            clean = display_symbol_name(name)
            if clean:
                yield SymbolDefinition(
                    stable_symbol_id(self.workspace_id, scope, clean, owner_tab_id),
                    clean,
                    str(value),
                    scope,
                    owner_tab_id,
                )


def definitions_payload(
    definitions: tuple[SymbolDefinition, ...],
) -> list[dict[str, object]]:
    """Serialize definitions without occurrence or offset caches."""

    return [
        {
            "symbol_id": item.symbol_id,
            "name": item.name,
            "value": item.value,
            "scope": item.scope.value,
            "owner_tab_id": item.owner_tab_id,
            "catalog_revision": item.catalog_revision,
            "resolution_revision": item.resolution_revision,
        }
        for item in definitions
    ]


def _modern_conflicts(payload, scope, key, raw, definitions) -> tuple[str, ...]:
    """Report malformed definitions and divergent compatibility mirrors."""

    conflicts: list[str] = []
    modern_values = {item.normalized_name: item.value for item in definitions}
    if len(modern_values) != len(definitions):
        conflicts.append(f"{key} contains duplicate normalized names.")
    mirror_key = "global_symbols" if scope is SymbolScope.GLOBAL else "symbols"
    if mirror_key in payload:
        mirror = {
            display_symbol_name(name).casefold(): value
            for name, value in _string_map(payload.get(mirror_key)).items()
        }
        if mirror != modern_values:
            conflicts.append(f"{mirror_key} differs from authoritative {key}.")
    if len(definitions) != len(raw):
        conflicts.append(f"{key} contains invalid definitions.")
    return tuple(conflicts)


def _definition(raw, scope, owner_tab_id) -> SymbolDefinition | None:
    """Deserialize one validated definition record."""

    if not isinstance(raw, Mapping):
        return None
    name = display_symbol_name(raw.get("name", ""))
    symbol_id = str(raw.get("symbol_id", "")).strip()
    if not name or not symbol_id:
        return None
    return SymbolDefinition(
        symbol_id, name, str(raw.get("value", "")), scope, owner_tab_id,
        int(raw.get("catalog_revision", 0)),
        int(raw.get("resolution_revision", 0)),
    )


def _string_map(raw: object) -> dict[str, str]:
    """Normalize a legacy mapping without retaining mutable input."""

    return (
        {str(key): str(value) for key, value in raw.items()}
        if isinstance(raw, Mapping) else {}
    )
