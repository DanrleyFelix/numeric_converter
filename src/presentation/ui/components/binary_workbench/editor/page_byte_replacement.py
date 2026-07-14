from src.core.binary_workbench.byte_replacement import (
    merged_byte_overlays,
    without_overlapping_instructions,
)
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES
from src.presentation.ui.components.binary_workbench.editor.page_overlays import overlay_bytes
from src.presentation.ui.components.binary_workbench.editor.page_reader import effective_reader_size


class EditorPageByteReplacementMixin:
    def replacement_bytes_at(self, start: int, size: int) -> bytes | None:
        """Read exact current bytes by seek or from complete assembly rows."""

        if self._reader is None:
            return self.grid.replacement_bytes_at(start, size)
        file_size = effective_reader_size(self._reader, self._context.file_size)
        if start < 0 or size < 0 or start > file_size:
            return None
        covered_size = min(size, file_size - start)
        extension_size = size - covered_size
        if extension_size and not self.grid.byte_shift_allowed():
            return None
        existing = self._read_visible_data(
            start,
            covered_size,
            overlay_bytes(self._context.byte_overlays),
        )
        return existing + bytes(extension_size)

    def replace_bytes_at(self, start: int, data: bytes) -> bool:
        """Apply byte replacement independently from the currently rendered viewport."""

        if self.replacement_bytes_at(start, len(data)) is None:
            return False
        if self._reader is None:
            return self.grid.replace_bytes_at(start, data)
        previous_size = effective_reader_size(self._reader, self._context.file_size)
        current_size = max(previous_size, start + len(data))
        self._update_context(
            {
                "byte_overlays": merged_byte_overlays(self._context.byte_overlays, start, data),
                "instruction_overlays": without_overlapping_instructions(
                    self._context.instruction_overlays,
                    start,
                    len(data),
                    ROW_BYTES,
                ),
                "file_size": current_size,
                "version_dirty": True,
            }
        )
        self.grid.set_virtual_total_size(current_size)
        visible_start = start - (start % ROW_BYTES)
        self._load_visible_rows(visible_start, self.grid.visible_size(), 1)
        if current_size > previous_size:
            self.structuralVersionSaveRequested.emit()
        return True
