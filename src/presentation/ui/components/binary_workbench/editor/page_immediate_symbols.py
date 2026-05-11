from __future__ import annotations

from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
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
        self.grid.set_symbols(labels, variables, equates)
        self._update_context(
            {
                "variables": variables,
                "equates": equates,
                "labels": labels,
                "rows": rows,
                "symbol_offsets": symbol_offsets(rows, variables, equates, labels),
            }
        )
