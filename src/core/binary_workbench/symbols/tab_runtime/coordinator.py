from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping

from src.core.binary_workbench.symbols.definitions import (
    GlobalSymbolRepository, LocalSymbolRepository, SymbolQueryService,
)
from src.core.binary_workbench.symbols.events import (
    InstructionReferencesReplaced, OffsetLayoutInvalidated,
    SymbolDefinitionsChanged, SymbolEventBus,
)
from src.core.binary_workbench.symbols.layout import (
    InstructionIdentityJournal, InstructionLayoutIndex,
)
from src.core.binary_workbench.symbols.occurrences import SymbolOccurrenceIndex
from src.core.binary_workbench.symbols.tab_runtime.queries import (
    SymbolRuntimeQueriesMixin,
)
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO

@dataclass(slots=True)
class MaterializedSymbolTab:
    """Hold indices created only after a tab is requested."""

    journal: InstructionIdentityJournal
    occurrences: SymbolOccurrenceIndex
    layout: InstructionLayoutIndex
    source_lines: list[str] | None = None
    source_search_text: str | None = None
    fully_indexed: bool = False
    complete_symbol_ids: set[str] | None = None
    source_revision: int = 0
    viewport_epoch: int = 0


class SymbolRuntime(SymbolRuntimeQueriesMixin):
    """Coordinate repositories and per-tab indices without eager tab work."""

    def __init__(self, workspace_id: str) -> None:
        self.workspace_id = workspace_id
        self.globals = GlobalSymbolRepository(workspace_id)
        self.locals = LocalSymbolRepository(workspace_id)
        self.query = SymbolQueryService(self.globals, self.locals)
        self.events = SymbolEventBus()
        self._tabs: dict[str, MaterializedSymbolTab] = {}

    def set_global_definitions(self, values: Mapping[str, str]) -> None:
        """Update the shared catalog without scanning source tabs."""

        revision = self.globals.revision
        self.globals.replace_all(values)
        if self.globals.revision != revision:
            self.events.publish(SymbolDefinitionsChanged(
                None, None, self.globals.revision,
                symbol_ids=tuple(item.symbol_id for item in self.globals.definitions()),
            ))

    def set_local_definitions(self, tab_id: str, values: Mapping[str, str]) -> None:
        """Update only one tab-owned repository."""

        repository = self.locals.for_tab(tab_id)
        revision = repository.revision
        repository.replace_all(values)
        if repository.revision != revision:
            self.events.publish(SymbolDefinitionsChanged(
                tab_id, None, repository.revision,
                symbol_ids=tuple(item.symbol_id for item in repository.definitions()),
            ))

    def materialize_tab(
        self,
        tab_id: str,
        rows: list[BinaryWorkbenchRowDTO],
        local_symbols: Mapping[str, str],
        base: int = 0,
        initial_range: tuple[int, int] | None = None,
    ) -> MaterializedSymbolTab:
        """Build occurrences and layout only for one requested tab."""

        self.set_local_definitions(tab_id, local_symbols)
        journal = InstructionIdentityJournal(self.workspace_id, tab_id, len(rows))
        layout = InstructionLayoutIndex(
            journal.ids, [_row_size(row) for row in rows], base,
            sequential_id_prefix=f"{tab_id}:", sequential_id_base=16,
        )
        occurrences = SymbolOccurrenceIndex(tab_id)
        source_lines = [row.instruction for row in rows]
        first, last = _materialized_range(initial_range, len(rows))
        occurrences.rebuild(
            (
                (journal.ids[index], source_lines[index])
                for index in range(first, last + 1)
            ),
            self.query.snapshot(tab_id),
        )
        tab = MaterializedSymbolTab(
            journal, occurrences, layout, source_lines,
            None, initial_range is None, set(),
        )
        self._tabs[tab_id] = tab
        return tab

    def is_materialized(self, tab_id: str) -> bool:
        """Return whether a tab owns occurrence and layout state."""

        return tab_id in self._tabs

    def discard_tab(self, tab_id: str) -> None:
        """Release occurrence and layout state for one tab."""

        self._tabs.pop(tab_id, None)

    def update_base(self, tab_id: str, base: int) -> None:
        """Update the first offset lazily in constant time."""

        if tab := self._tabs.get(tab_id):
            tab.layout.set_base(base)
            self.events.publish(OffsetLayoutInvalidated(
                tab_id, None, self.globals.revision,
                source_revision=tab.source_revision,
                first_instruction_id=(tab.journal.ids[0] if tab.journal.ids else None),
            ))

    def replace_instruction(self, tab_id: str, line: int, text: str) -> None:
        """Reindex one edited line and emit one aggregate event."""

        tab = self._tabs.get(tab_id)
        if tab is None or not 0 <= line < len(tab.journal.ids):
            return
        if tab.source_lines is not None:
            tab.source_lines[line] = text
            tab.source_search_text = None
        instruction_id = tab.journal.ids[line]
        diff = tab.occurrences.replace_instruction_references(
            instruction_id, text, self.query.snapshot(tab_id)
        )
        if diff.added or diff.removed or diff.changed:
            tab.source_revision += 1
            self.events.publish(InstructionReferencesReplaced(
                tab_id, None, self.globals.revision,
                source_revision=tab.source_revision,
                instruction_ids=(instruction_id,),
            ))


def _row_size(row: BinaryWorkbenchRowDTO) -> int:
    """Return the bytes emitted by one already-derived row."""

    try:
        return len(bytes.fromhex(row.bytes_text.replace(" ", "")))
    except ValueError:
        return 0


def _materialized_range(value: tuple[int, int] | None, count: int) -> tuple[int, int]:
    """Clamp an initial viewport range to existing rows."""

    if value is None:
        return 0, count - 1
    return max(0, value[0]), min(count - 1, value[1])
