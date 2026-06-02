from pathlib import Path

from src.core.binary_workbench.block_reader import CachedBinaryReader
from src.core.binary_workbench.context_overlays import compact_binary_context_overlays
from src.core.binary_workbench.mips_r3000a import build_rows_from_bytes
from src.modules.dtos import BinaryWorkbenchTabContextDTO
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_TAB_KIND,
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import (
    apply_instruction_overlays,
    file_offset,
    merged_instruction_labels,
    rows_from_overlays,
    update_instruction_overlays,
)
from src.presentation.ui.components.binary_workbench.symbols import symbol_offsets


class EditorPageBinaryLoadingMixin:
    def _load_visible_rows(self, offset: int, size: int, direction: int) -> None:
        if self._loading_visible_rows or self._reader is None:
            return
        self._loading_visible_rows = True
        visible_offset = max(0, offset)
        self._reader.prefetch_for_offset(visible_offset, direction)
        source_data = self._reader.read(visible_offset, size, {})
        rows = build_rows_from_bytes(
            source_data,
            list(self._context.reference_offsets),
            visible_offset,
            dict(self._context.reference_offset_bases),
        )
        self._context = compact_binary_context_overlays(self._context)
        if self._context.byte_overlays:
            data = self._reader.read(visible_offset, size, overlay_bytes(self._context.byte_overlays))
            rows = build_rows_from_bytes(
                data,
                list(self._context.reference_offsets),
                visible_offset,
                dict(self._context.reference_offset_bases),
            )
        rows = apply_instruction_overlays(rows, self._context.instruction_overlays)
        self.grid.render_rows(rows, visible_offset)
        self._select_pending_offset()
        self._loading_visible_rows = False
        labels = merged_instruction_labels(rows, self._context.instruction_overlays)
        symbol_rows = [*rows, *rows_from_overlays(self._context.instruction_overlays)]
        self.grid.set_symbols(labels, self._context.variables, self._context.equates)
        self._context = BinaryWorkbenchTabContextDTO(
            **{
                **self._context.__dict__,
                "rows": rows,
                "file_size": self._reader.file_size,
                "last_open_offset": f"0x{visible_offset:08X}",
                "labels": labels,
                "symbol_offsets": symbol_offsets(symbol_rows, self._context.variables, self._context.equates, labels),
            }
        )
        self.contextChanged.emit(self._context)

    def _update_overlay(self, rows: list) -> None:
        if self._reader is None:
            return
        if self.grid.edit_origin_kind() not in {BINARY_WORKBENCH_TEXT.BYTES, BINARY_WORKBENCH_TEXT.INSTRUCTION}:
            return
        overlays = dict(self._context.byte_overlays)
        instruction_overlays = self._instruction_overlays_for_rows(rows)
        for row in rows:
            offset = int(row.offsets.get("File", "0x0"), 16)
            current = bytes.fromhex(row.bytes_text.replace(" ", ""))
            original = self._reader.read(offset, len(current), {})
            key = f"0x{offset:08X}"
            overlays.pop(key, None) if current == original else overlays.__setitem__(key, row.bytes_text)
        if overlays == self._context.byte_overlays and instruction_overlays == self._context.instruction_overlays:
            return
        labels = merged_instruction_labels(rows, instruction_overlays)
        symbol_rows = [*rows, *rows_from_overlays(instruction_overlays)]
        self._context = BinaryWorkbenchTabContextDTO(
            **{
                **self._context.__dict__,
                "byte_overlays": overlays,
                "instruction_overlays": instruction_overlays,
                "rows": rows,
                "labels": labels,
                "version_dirty": True,
                "symbol_offsets": symbol_offsets(symbol_rows, self._context.variables, self._context.equates, labels),
            }
        )
        self.contextChanged.emit(self._context)

    def _instruction_overlays_for_rows(self, rows: list) -> dict[str, str]:
        origin = self.grid.edit_origin_kind()
        if origin == BINARY_WORKBENCH_TEXT.INSTRUCTION:
            return update_instruction_overlays(self._context.instruction_overlays, rows, self._context.rows)
        if origin == BINARY_WORKBENCH_TEXT.BYTES:
            return instruction_overlays_with_changed_rows(
                self._context.instruction_overlays,
                rows,
                self._context.rows,
            )
        if self.grid.focused_editor_kind() != BINARY_WORKBENCH_TEXT.INSTRUCTION:
            return dict(self._context.instruction_overlays)
        return update_instruction_overlays(self._context.instruction_overlays, rows, self._context.rows)

    def _reader_for_context(
        self,
        context: BinaryWorkbenchTabContextDTO,
    ) -> CachedBinaryReader | None:
        if context.kind != BINARY_WORKBENCH_TAB_KIND.BINARY:
            return None
        if context.read_mode == "assembly" or not context.source_path:
            return None
        path = Path(context.source_path)
        if not path.exists():
            return None
        return CachedBinaryReader(path, self._preferences.block_size, self._preferences.cache_max_blocks)


def overlay_bytes(values: dict[str, str]) -> dict[int, bytes]:
    return {
        int(offset, 16): bytes.fromhex(bytes_text.replace(" ", ""))
        for offset, bytes_text in values.items()
    }


def instruction_overlays_with_changed_rows(
    overlays: dict[str, str],
    rows: list,
    previous_rows: list,
) -> dict[str, str]:
    updated = dict(overlays)
    previous_bytes = {file_offset(row): row.bytes_text for row in previous_rows}
    for row in rows:
        offset = file_offset(row)
        if previous_bytes.get(offset) != row.bytes_text:
            updated[offset] = row.instruction
    return updated
