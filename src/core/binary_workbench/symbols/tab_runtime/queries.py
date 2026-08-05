from __future__ import annotations

from src.core.binary_workbench.symbols.compatibility import LegacySymbolOffsetsAdapter
from src.core.binary_workbench.symbols.definitions import normalize_symbol_name
from src.core.binary_workbench.symbols.occurrences import SYMBOL_TOKEN


class SymbolRuntimeQueriesMixin:
    """Provide selected-Symbol queries without building global offset maps."""

    def offsets_for(self, tab_id: str, symbol_name: str) -> list[str]:
        """Resolve only one selected Symbol's offsets in one tab."""

        tab = self._tabs.get(tab_id)
        if tab is None:
            return []
        snapshot = self.query.snapshot(tab_id)
        definition = snapshot.resolve(symbol_name)
        if definition is None:
            return []
        if (
            not tab.fully_indexed
            and definition.symbol_id not in (tab.complete_symbol_ids or set())
        ):
            self._complete_selected_symbol(tab_id, definition.normalized_name)
        names = {
            name: item.symbol_id
            for name, item in {
                **snapshot.global_by_name,
                **snapshot.local_by_name,
            }.items()
        }
        return LegacySymbolOffsetsAdapter(
            tab.occurrences, tab.layout, names
        ).offsets_for(tab_id, normalize_symbol_name(symbol_name))

    def lines_for_symbols(self, tab_id: str, names: set[str]) -> tuple[int, ...]:
        """Locate changed definitions without comparing lines to the catalog."""

        tab = self._tabs.get(tab_id)
        if tab is None or tab.source_lines is None or not names:
            return ()
        if tab.source_search_text is None:
            tab.source_search_text = "\n".join(tab.source_lines).casefold()
        normalized = {normalize_symbol_name(name) for name in names}
        if len(normalized) <= 8:
            return tuple(sorted({
                line
                for name in normalized
                for line in matching_source_lines(tab.source_search_text, name)
            }))
        matches: list[int] = []
        for line, text in enumerate(tab.source_lines):
            if any(
                match.group(2).casefold() in normalized
                for match in SYMBOL_TOKEN.finditer(text)
            ):
                matches.append(line)
        return tuple(matches)

    def _complete_selected_symbol(self, tab_id: str, normalized_name: str) -> None:
        """Scan source once for one requested name instead of all Symbols."""

        tab = self._tabs[tab_id]
        snapshot = self.query.snapshot(tab_id)
        definition = snapshot.resolve(normalized_name)
        if definition is None or tab.source_lines is None:
            return
        ids = tab.journal.ids
        if tab.source_search_text is None:
            tab.source_search_text = "\n".join(tab.source_lines).casefold()
        for index in matching_source_lines(tab.source_search_text, normalized_name):
            tab.occurrences.replace_instruction_references(
                ids[index], tab.source_lines[index], snapshot
            )
        if tab.complete_symbol_ids is None:
            tab.complete_symbol_ids = set()
        tab.complete_symbol_ids.add(definition.symbol_id)


def matching_source_lines(source: str, normalized_name: str) -> tuple[int, ...]:
    """Locate one requested Symbol without parsing every source line."""

    positions: list[int] = []
    for sigil in ("_", "@"):
        token = f"{sigil}{normalized_name}"
        position = source.find(token)
        while position >= 0:
            end = position + len(token)
            before_valid = position == 0 or not (
                source[position - 1].isalnum() or source[position - 1] == "_"
            )
            after_valid = end == len(source) or not (
                source[end].isalnum() or source[end] == "_"
            )
            if before_valid and after_valid:
                positions.append(position)
            position = source.find(token, position + 1)
    if not positions:
        return ()
    rows: list[int] = []
    previous_position = 0
    current_line = 0
    for position in sorted(positions):
        current_line += source.count("\n", previous_position, position)
        if not rows or rows[-1] != current_line:
            rows.append(current_line)
        previous_position = position
    return tuple(rows)
