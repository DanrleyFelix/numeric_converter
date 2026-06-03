from __future__ import annotations

from src.core.binary_workbench.version_overlays import (
    byte_overlays_from_instruction_overlays,
)
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TAB_KIND
from src.presentation.ui.components.binary_workbench.editor.immediate_symbol_dialog import (
    ImmediateSymbolNameDialog,
)
from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import (
    labels_from_rows,
)
from src.presentation.ui.components.binary_workbench.symbols import symbol_offsets


class EditorPageImmediateSymbolsMixin:
    def _add_immediate_symbol(self, kind: str, value: str) -> None:
        dialog = ImmediateSymbolNameDialog(kind, value, self)
        if dialog.exec() != dialog.DialogCode.Accepted or not dialog.symbol_name():
            return
        variables = dict(self._context.variables)
        equates = dict(self._context.equates)
        if kind == BINARY_WORKBENCH_TEXT.VARIABLE_TARGET:
            variables[dialog.symbol_name()] = value
        else:
            equates[dialog.symbol_name()] = value
        labels = labels_from_rows(self.grid.export_rows())
        rows = self.grid.rows_encoded_with_symbols(variables, equates, labels)
        labels = labels_from_rows(rows)
        self.grid.set_symbols(labels, variables, equates)
        updates: dict[str, object] = {
            "variables": variables,
            "equates": equates,
            "labels": labels,
            "rows": rows,
            "symbol_offsets": symbol_offsets(rows, variables, equates, labels),
        }
        if self._context.kind == BINARY_WORKBENCH_TAB_KIND.BINARY:
            updates["byte_overlays"] = _byte_overlays_with_symbol_values(
                self._context.instruction_overlays,
                self._context.byte_overlays,
                variables,
                equates,
            )
        self._update_context(updates)


def _byte_overlays_with_symbol_values(
    instruction_overlays: dict[str, str],
    byte_overlays: dict[str, str],
    variables: dict[str, str],
    equates: dict[str, str],
) -> dict[str, str]:
    instruction_offsets = set(instruction_overlays)
    updated = {
        offset: value
        for offset, value in byte_overlays.items()
        if offset not in instruction_offsets
    }
    updated.update(byte_overlays_from_instruction_overlays(instruction_overlays, variables, equates))
    return updated
