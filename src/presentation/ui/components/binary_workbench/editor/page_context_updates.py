from src.modules.binary_workbench_dtos import BinaryWorkbenchTabContextDTO
from src.core.binary_workbench.version_overlays import without_blank_instruction_overlays
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_TAB_KIND,
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
        self.contextChanged.emit(self._context)


def symbol_updates(context: BinaryWorkbenchTabContextDTO, rows: list) -> dict[str, object]:
    labels = labels_from_rows(rows)
    updates = {
        "rows": rows,
        "labels": labels,
        "version_dirty": context.kind == BINARY_WORKBENCH_TAB_KIND.BINARY,
        "symbol_offsets": symbol_offsets(rows, context.variables, context.equates, labels),
    }
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
