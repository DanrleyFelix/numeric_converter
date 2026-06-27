from pathlib import Path

from src.core.binary_workbench.version_overlays import without_blank_instruction_overlays
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_TAB_KIND
from src.modules.binary_workbench_dtos import BinaryWorkbenchTabContextDTO
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_LAYOUT,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import (
    labels_from_rows,
)
from src.presentation.ui.components.binary_workbench.editor.selection_summary import (
    update_selection_summary,
)
from src.presentation.ui.components.binary_workbench.symbols import symbol_offsets


class EditorPageContextMixin:
    def _on_rows_changed(self, rows: list) -> None:
        if self._reader is not None:
            self._update_overlay(rows)
            return
        self._update_context(symbol_updates(self._context, rows))

    def _on_commands_changed(self, commands: dict[str, list[str]]) -> None:
        self._update_context({"custom_commands": commands})

    def _set_summary(self, text: str) -> None:
        update_selection_summary(
            (self.offset_summary, self.summary, self.length_summary),
            text or BINARY_WORKBENCH_TEXT.SELECTION_EMPTY,
        )

    def _set_cpu_arch_summary(self, value: str) -> None:
        self.cpu_arch_summary.setText(BINARY_WORKBENCH_TEXT.CPU_ARCH_SUMMARY_TEMPLATE.format(cpu_arch=value))

    def _set_internal_file_summary(self, context: BinaryWorkbenchTabContextDTO) -> None:
        if context.kind != BINARY_WORKBENCH_TAB_KIND.INTERNAL or not context.source_path:
            self.internal_file_summary.clear()
            self.internal_file_summary.setVisible(False)
            return
        name = Path(context.source_path).name[:BINARY_WORKBENCH_LAYOUT.INTERNAL_FILE_SUMMARY_MAX_CHARS]
        self.internal_file_summary.setText(
            BINARY_WORKBENCH_TEXT.INTERNAL_FILE_SUMMARY_TEMPLATE.format(name=name)
        )
        self.internal_file_summary.setVisible(True)

    def _visible_columns(self) -> list[str]:
        visible = self._context.view_preferences.visible_columns
        offsets = [
            name
            for name in self._context.reference_offsets
            if visible.get(name, True)
        ]
        columns = [*offsets]
        if visible.get(BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS, True):
            columns.append(BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS)
        if visible.get(BINARY_WORKBENCH_TEXT.BYTES, True):
            columns.append(BINARY_WORKBENCH_TEXT.BYTES)
        if visible.get(BINARY_WORKBENCH_TEXT.DECODED_TEXT, False):
            columns.append(BINARY_WORKBENCH_TEXT.DECODED_TEXT)
        columns.append(BINARY_WORKBENCH_TEXT.INSTRUCTION)
        return columns

    def _update_context(self, updates: dict[str, object]) -> None:
        self._context = BinaryWorkbenchTabContextDTO(**{**self._context.__dict__, **updates})
        self._set_cpu_arch_summary(self._context.cpu_arch)
        self._set_internal_file_summary(self._context)
        self._emit_context_changed()

    def _emit_context_changed(self) -> None:
        if getattr(self, "_suppress_context_changed", False):
            return
        self.contextChanged.emit(self._context)


def symbol_updates(context: BinaryWorkbenchTabContextDTO, rows: list) -> dict[str, object]:
    labels = labels_from_rows(rows)
    updates = {
        "rows": rows,
        "labels": labels,
        "version_dirty": context.kind == BINARY_WORKBENCH_TAB_KIND.BINARY,
        "symbol_offsets": symbol_offsets(rows, context.variables, context.equates, labels),
    }
    if context.kind == BINARY_WORKBENCH_TAB_KIND.INTERNAL:
        return _internal_updates(context, rows, updates)
    if context.kind != BINARY_WORKBENCH_TAB_KIND.BINARY:
        return updates
    instruction_overlays = {
        row.offsets.get("File", "0x00000000"): row.instruction
        for row in rows
        if row.instruction and row.offsets.get("File") != "-"
    }
    byte_overlays = {
        row.offsets.get("File", "0x00000000"): row.bytes_text
        for row in rows
        if row.bytes_text and row.offsets.get("File") != "-"
    }
    byte_overlays, instruction_overlays = without_blank_instruction_overlays(
        byte_overlays,
        instruction_overlays,
    )
    return {
        **updates,
        "byte_overlays": byte_overlays,
        "instruction_overlays": instruction_overlays,
    }


def _internal_updates(
    context: BinaryWorkbenchTabContextDTO,
    rows: list,
    updates: dict[str, object],
) -> dict[str, object]:
    original = {row.offsets.get("File"): row for row in context.original_rows}
    byte_overlays: dict[str, str] = {}
    instruction_overlays: dict[str, str] = {}
    for row in rows:
        offset = row.offsets.get("File")
        if not offset or offset == "-":
            continue
        source = original.get(offset)
        if source is None or source.bytes_text != row.bytes_text:
            byte_overlays[offset] = row.bytes_text
        if source is None or source.instruction != row.instruction:
            instruction_overlays[offset] = row.instruction
    byte_overlays, instruction_overlays = without_blank_instruction_overlays(
        byte_overlays,
        instruction_overlays,
    )
    return {
        **updates,
        "version_dirty": bool(byte_overlays or instruction_overlays),
        "byte_overlays": byte_overlays,
        "instruction_overlays": instruction_overlays,
    }
