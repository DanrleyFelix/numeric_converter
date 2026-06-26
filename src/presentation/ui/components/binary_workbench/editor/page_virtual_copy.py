from PySide6.QtWidgets import QApplication

from src.core.binary_workbench.mips_r3000a import build_rows_from_bytes
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.instruction_overlays import (
    apply_instruction_overlays,
)
from src.presentation.ui.components.binary_workbench.editor.page_overlays import (
    overlay_bytes,
)


class EditorPageVirtualCopyMixin:
    def _copy_virtual_selection(self, kind: str, start_offset: int, end_offset: int) -> None:
        if self._reader is None:
            return
        if kind == BINARY_WORKBENCH_TEXT.BYTES:
            text = self._copy_virtual_bytes(start_offset, end_offset)
        elif kind == BINARY_WORKBENCH_TEXT.RAW_INSTRUCTIONS:
            text = self._copy_virtual_raw_instructions(start_offset, end_offset)
        else:
            text = self._copy_virtual_instructions(start_offset, end_offset)
        QApplication.clipboard().setText(text)

    def _copy_virtual_bytes(self, start_offset: int, end_offset: int) -> str:
        size = max(0, end_offset - start_offset + 1)
        data = self._reader.read_uncached(start_offset, size, overlay_bytes(self._context.byte_overlays))
        raw = data.hex().upper()
        return "\n".join(
            self.grid._display_bytes_text(raw[index : index + 8])
            for index in range(0, len(raw), 8)
        )

    def _copy_virtual_instructions(self, start_offset: int, end_offset: int) -> str:
        rows = self._virtual_rows(start_offset, end_offset)
        return "\n".join(self.grid._display_instruction(row.instruction) for row in rows)

    def _copy_virtual_raw_instructions(self, start_offset: int, end_offset: int) -> str:
        return "\n".join(
            self.grid._raw_instruction_from_bytes(row.bytes_text, int(row.offsets["File"], 16))
            for row in self._virtual_rows(start_offset, end_offset)
        )

    def _virtual_rows(self, start_offset: int, end_offset: int) -> list:
        word_size = self.grid._codec.word_size
        aligned_start = start_offset - (start_offset % word_size)
        aligned_end = end_offset - (end_offset % word_size)
        size = max(0, aligned_end - aligned_start + word_size)
        data = self._reader.read_uncached(aligned_start, size, overlay_bytes(self._context.byte_overlays))
        rows = build_rows_from_bytes(
            data,
            list(self._context.reference_offsets),
            aligned_start,
            dict(self._context.reference_offset_bases),
        )
        return apply_instruction_overlays(rows, self._context.instruction_overlays)
