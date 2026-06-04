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
    update_instruction_overlays,
)
from src.presentation.ui.components.binary_workbench.symbols import symbol_offsets


class EditorPageImmediateSymbolsMixin:
    def _add_immediate_symbol(self, kind: str, value: str, start: int = -1, end: int = -1) -> None:
        dialog = ImmediateSymbolNameDialog(kind, value, self)
        if dialog.exec() != dialog.DialogCode.Accepted or not dialog.symbol_name():
            return
        name = dialog.symbol_name()
        replacement = _replacement_range(kind, name, start, end)
        variables = dict(self._context.variables)
        equates = dict(self._context.equates)
        if kind == BINARY_WORKBENCH_TEXT.VARIABLE_TARGET:
            variables[name] = value
        else:
            equates[name] = value
        labels = labels_from_rows(self.grid.export_rows())
        rows = self.grid.rows_encoded_with_symbols(variables, equates, labels, replacement)
        labels = labels_from_rows(rows)
        offsets = symbol_offsets(rows, variables, equates, labels)
        self.grid.set_symbols(labels, variables, equates, offsets)
        updates: dict[str, object] = {
            "variables": variables,
            "equates": equates,
            "labels": labels,
            "rows": rows,
            "symbol_offsets": offsets,
        }
        if self._context.kind == BINARY_WORKBENCH_TAB_KIND.BINARY:
            instruction_overlays = update_instruction_overlays(
                self._context.instruction_overlays,
                rows,
                self._context.rows,
            )
            updates["instruction_overlays"] = instruction_overlays
            updates["byte_overlays"] = _byte_overlays_with_symbol_values(
                instruction_overlays,
                self._context.byte_overlays,
                variables,
                equates,
            )
            if replacement is not None:
                updates["version_dirty"] = True
        self._update_context(updates)
        if replacement is not None:
            self.load_context(self._context)


def _replacement_range(
    kind: str,
    name: str,
    start: int,
    end: int,
) -> tuple[int, int, str] | None:
    if start < 0 or end <= start:
        return None
    prefix = "_" if kind == BINARY_WORKBENCH_TEXT.VARIABLE_TARGET else "@"
    return start, end, f"{prefix}{name.lstrip(prefix)}"


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
