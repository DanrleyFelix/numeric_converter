from src.core.binary_workbench.context_overlays import compact_binary_context_overlays
from src.core.binary_workbench.mips_r3000a import build_rows_from_bytes
from src.core.binary_workbench.symbolic_replacements import apply_symbol_offsets
from src.modules.binary_workbench_dtos import BinaryWorkbenchTabContextDTO
from src.presentation.ui.components.binary_workbench.constants import (
    BINARY_WORKBENCH_TEXT,
)
from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import (
    apply_instruction_overlays,
    merged_instruction_labels,
    rows_from_overlays,
)
from src.presentation.ui.components.binary_workbench.editor.page_reader import (
    effective_reader_size,
    with_internal_binary_offsets,
)
from src.presentation.ui.components.binary_workbench.editor.page_overlays import (
    apply_overlay_bytes,
    overlay_bytes,
)
from src.presentation.ui.components.binary_workbench.editor.page_version_rows import (
    active_version_rows,
    instruction_overlays_for_rows,
)
from src.presentation.ui.components.binary_workbench.symbols import symbol_offsets


class EditorPageBinaryLoadingMixin:
    def _load_visible_rows(self, offset: int, size: int, direction: int) -> None:
        if self._loading_visible_rows or self._reader is None:
            return
        self._loading_visible_rows = True
        visible_offset = max(0, offset)
        self._reader.prefetch_for_offset(visible_offset, direction)
        source_data = self._read_visible_data(visible_offset, size, {})
        rows = build_rows_from_bytes(
            source_data,
            list(self._context.reference_offsets),
            visible_offset,
            dict(self._context.reference_offset_bases),
        )
        rows = with_internal_binary_offsets(self._reader, rows)
        self._context = compact_binary_context_overlays(self._context)
        if self._context.byte_overlays:
            data = self._read_visible_data(
                visible_offset,
                size,
                overlay_bytes(self._context.byte_overlays),
            )
            rows = build_rows_from_bytes(
                data,
                list(self._context.reference_offsets),
                visible_offset,
                dict(self._context.reference_offset_bases),
            )
            rows = with_internal_binary_offsets(self._reader, rows)
        rows = apply_instruction_overlays(rows, self._context.instruction_overlays)
        rows = active_version_rows(self._context, rows)
        rows = apply_symbol_offsets(
            rows,
            self._context.variables,
            self._context.equates,
            self._context.symbol_offsets,
            self.grid._codec,
        )
        self.grid.render_rows(rows, visible_offset)
        self.grid.set_virtual_total_size(self._reader.file_size)
        original_size = effective_reader_size(
            self._reader,
            self._context.original_file_size,
        )
        self.grid.set_original_file_size(original_size)
        self._select_pending_offset()
        self._loading_visible_rows = False
        labels = merged_instruction_labels(rows, self._context.instruction_overlays)
        symbol_rows = [*rows, *rows_from_overlays(self._context.instruction_overlays)]
        self.grid.set_symbols(labels, self._context.variables, self._context.equates, self._context.symbol_offsets)
        self._context = BinaryWorkbenchTabContextDTO(
            **{
                **self._context.__dict__,
                "rows": rows,
                "file_size": effective_reader_size(self._reader, self._context.file_size),
                "original_file_size": original_size,
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
        instruction_overlays = instruction_overlays_for_rows(self._context, self.grid, rows)
        file_size = self._context.original_file_size or self._reader.file_size
        for row in rows:
            try:
                offset = int(row.offsets.get("File", "0x0"), 16)
            except ValueError:
                continue
            current = bytes.fromhex(row.bytes_text.replace(" ", ""))
            file_size = max(file_size, offset + len(current))
            original = self._reader.read(offset, len(current), {})
            key = f"0x{offset:08X}"
            overlays.pop(key, None) if current == original else overlays.__setitem__(key, row.bytes_text)
        for offset, bytes_text in overlays.items():
            try:
                file_size = max(file_size, int(offset, 16) + (len(bytes_text.replace(" ", "")) // 2))
            except ValueError:
                continue
        if (
            overlays == self._context.byte_overlays
            and instruction_overlays == self._context.instruction_overlays
            and file_size == self._context.file_size
            and rows == self._context.rows
        ):
            return
        labels = merged_instruction_labels(rows, instruction_overlays)
        symbol_rows = [*rows, *rows_from_overlays(instruction_overlays)]
        self._context = BinaryWorkbenchTabContextDTO(
            **{
                **self._context.__dict__,
                "byte_overlays": overlays,
                "instruction_overlays": instruction_overlays,
                "rows": rows,
                "file_size": file_size,
                "labels": labels,
                "version_dirty": True,
                "symbol_offsets": symbol_offsets(symbol_rows, self._context.variables, self._context.equates, labels),
            }
        )
        self.contextChanged.emit(self._context)

    def _read_visible_data(
        self,
        offset: int,
        size: int,
        overlays: dict[int, bytes],
    ) -> bytes:
        if self._reader is None:
            return b""
        effective_size = effective_reader_size(self._reader, self._context.file_size)
        if size <= 0 or offset >= effective_size:
            return b""
        target_size = min(size, effective_size - offset)
        source_size = min(target_size, max(0, self._reader.file_size - offset))
        data = self._reader.read(offset, source_size, {})
        if len(data) < target_size:
            data += b"\x00" * (target_size - len(data))
        return apply_overlay_bytes(offset, data, overlays)
