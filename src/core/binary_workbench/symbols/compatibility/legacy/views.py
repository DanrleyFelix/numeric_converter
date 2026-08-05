from __future__ import annotations

from collections.abc import Iterator, Mapping

from src.core.binary_workbench.symbol_values import merged_symbol_values
from src.core.binary_workbench.symbols.definitions import SymbolDefinition
from src.core.binary_workbench.symbols.layout import InstructionLayoutIndex
from src.core.binary_workbench.symbols.occurrences import SymbolOccurrenceIndex


class LegacySymbolsMappingView(Mapping[str, str]):
    """Expose modern definitions as a read-only legacy mapping."""

    def __init__(self, definitions: tuple[SymbolDefinition, ...]) -> None:
        self._by_name = {item.name: item.value for item in definitions}

    def __getitem__(self, key: str) -> str:
        return self._by_name[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._by_name)

    def __len__(self) -> int:
        return len(self._by_name)


class LegacySymbolMutationAdapter:
    """Translate old map replacement APIs to one canonical map."""

    @staticmethod
    def values(
        symbols: Mapping[str, str] | None = None,
        variables: Mapping[str, str] | None = None,
        equates: Mapping[str, str] | None = None,
    ) -> dict[str, str]:
        """Preserve variables to equates to symbols precedence."""

        return merged_symbol_values(
            dict(symbols or {}), dict(variables or {}), dict(equates or {})
        )


class LegacySymbolOffsetsAdapter:
    """Serve old offset consumers from occurrence and layout indices."""

    def __init__(
        self,
        occurrences: SymbolOccurrenceIndex,
        layout: InstructionLayoutIndex,
        symbol_ids_by_name: Mapping[str, str],
    ) -> None:
        self._occurrences = occurrences
        self._layout = layout
        self._symbol_ids_by_name = symbol_ids_by_name

    def offsets_for(self, tab_id: str, symbol_name: str) -> list[str]:
        """Materialize strings only for one requested Symbol and tab."""

        if tab_id != self._occurrences.tab_id:
            return []
        symbol_id = self._symbol_ids_by_name.get(symbol_name.casefold())
        if symbol_id is None:
            return []
        return [
            f"0x{value:08X}"
            for value in self._layout.offsets_for(symbol_id, self._occurrences)
        ]
