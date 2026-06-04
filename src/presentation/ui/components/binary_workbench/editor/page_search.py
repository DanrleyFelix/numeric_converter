from src.core.binary_workbench.text_search import (
    ansi_text_bytes,
    find_bytes_in_data,
    find_bytes_in_rows,
)
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.page_binary_loading import (
    overlay_bytes,
)


class EditorPageSearchMixin:
    def commit_current_editor_text(self) -> None:
        self.grid.commit_current_editor_text()

    def go_to_offset(self, offset: int) -> None:
        self.commit_current_editor_text()
        self._pending_selection = (offset, offset)
        self.grid.set_visible_offset(offset)
        if self._reader is None:
            self._select_pending_offset()

    def go_to_instruction_offset(self, offset: int) -> None:
        self.commit_current_editor_text()
        self._pending_selection = (offset, offset)
        self.grid.set_visible_offset(offset)
        if self._reader is None:
            self.grid.select_instruction_offsets(offset, offset)
            self._pending_selection = None

    def find_text(
        self,
        mode: str,
        query: str,
        start_offset: int | None = None,
        end_offset: int | None = None,
    ) -> bool:
        results = self.find_offsets(mode, query, start_offset, end_offset)
        if results:
            self.go_to_offset(results[0])
            return True
        return False

    def find_offsets(
        self,
        mode: str,
        query: str,
        start_offset: int | None = None,
        end_offset: int | None = None,
    ) -> list[int]:
        if start_offset is not None and end_offset is not None and start_offset > end_offset:
            return []
        if mode == BINARY_WORKBENCH_TEXT.FIND_HEX_BYTES:
            return self._find_hex_bytes(query, start_offset, end_offset)
        if mode == BINARY_WORKBENCH_TEXT.FIND_ASSEMBLY:
            return self._find_instruction(query, start_offset, end_offset)
        if mode == BINARY_WORKBENCH_TEXT.FIND_DECODED_TEXT:
            return self._find_decoded_text(query, start_offset, end_offset)
        return []

    def _find_instruction(
        self,
        query: str,
        start_offset: int | None = None,
        end_offset: int | None = None,
    ) -> list[int]:
        needle = query.strip().lower()
        if not needle:
            return []
        rows = self.grid.export_rows() or self._context.rows
        return [
            offset
            for row in rows
            if row.offsets.get("File") != "-"
            and (offset := int(row.offsets.get("File", "0x0"), 16)) >= (start_offset or 0)
            and (end_offset is None or offset <= end_offset)
            and needle in row.instruction.lower()
        ]

    def _find_hex_bytes(
        self,
        query: str,
        start_offset: int | None = None,
        end_offset: int | None = None,
    ) -> list[int]:
        needle = hex_query_bytes(query)
        if not needle:
            return []
        return self._find_bytes(needle, start_offset, end_offset)

    def _find_decoded_text(
        self,
        query: str,
        start_offset: int | None = None,
        end_offset: int | None = None,
    ) -> list[int]:
        needle = ansi_text_bytes(query.strip())
        if not needle:
            return []
        return self._find_bytes(needle, start_offset, end_offset)

    def _find_bytes(
        self,
        needle: bytes,
        start_offset: int | None = None,
        end_offset: int | None = None,
    ) -> list[int]:
        if self._reader is None:
            return find_bytes_in_rows(self._context.rows, needle, start_offset, end_offset)
        offset = max(0, start_offset or 0)
        search_end = self._reader.file_size - 1 if end_offset is None else min(end_offset, self._reader.file_size - 1)
        if search_end < offset:
            return []
        carry = b""
        results: list[int] = []
        overlays = overlay_bytes(self._context.byte_overlays)
        block_size = self._preferences.block_size
        while offset <= search_end:
            data = self._reader.read(offset, min(block_size, search_end - offset + 1), overlays)
            haystack = carry + data
            results.extend(find_bytes_in_data(haystack, offset - len(carry), needle, start_offset, search_end))
            carry = haystack[-max(0, len(needle) - 1) :]
            offset += max(1, block_size)
        return results


def hex_query_bytes(value: str) -> bytes:
    try:
        return bytes.fromhex(value.replace(" ", ""))
    except ValueError:
        return b""
