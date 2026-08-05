from __future__ import annotations

from src.core.binary_workbench.version_overlays import (
    byte_overlays_from_instruction_overlays,
)
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_TAB_KIND
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.immediate_symbol_dialog import (
    ImmediateSymbolNameDialog,
)
from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import (
    labels_from_rows,
    update_instruction_overlays,
)
from src.presentation.ui.components.binary_workbench.editor.cursor_guard import (
    set_cursor_position,
)


class EditorPageImmediateSymbolsMixin:
    def _add_immediate_symbol(self, kind: str, value: str, start: int = -1, end: int = -1) -> None:
        cursor = self.grid.instructions.textCursor()
        cursor_state = (cursor.blockNumber(), cursor.positionInBlock())
        dialog = ImmediateSymbolNameDialog(kind, value, self)
        if dialog.exec() != dialog.DialogCode.Accepted or not dialog.symbol_name():
            return
        name = dialog.symbol_name()
        replacement = _replacement_range(kind, name, start, end)
        local_symbols = dict(self._context.symbols)
        local_symbols[name] = value
        variables = dict(self._context.variables)
        variables[name] = value
        equates = dict(variables)
        labels = labels_from_rows(self.grid.export_rows())
        rows = self.grid.rows_encoded_with_symbols(variables, equates, labels, replacement)
        labels = labels_from_rows(rows)
        offsets = {label: [offset] for label, offset in labels.items()}
        self.grid.set_symbols(labels, variables, equates, offsets)
        updates: dict[str, object] = {
            "symbols": local_symbols,
            "variables": variables,
            "equates": equates,
            "labels": labels,
            "rows": rows,
            "symbol_offsets": offsets,
        }
        if self._context.kind in {
            BINARY_WORKBENCH_TAB_KIND.BINARY,
            BINARY_WORKBENCH_TAB_KIND.INTERNAL,
        }:
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
        block = self.grid.instructions.document().findBlockByNumber(cursor_state[0])
        if block.isValid():
            cursor = self.grid.instructions.textCursor()
            set_cursor_position(cursor, block.position() + min(cursor_state[1], len(block.text())))
            self.grid.instructions.setTextCursor(cursor)
            self.grid.instructions.setFocus()


def _replacement_range(
    kind: str,
    name: str,
    start: int,
    end: int,
) -> tuple[int, int, str] | None:
    if start < 0 or end <= start:
        return None
    prefix = "_"
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
