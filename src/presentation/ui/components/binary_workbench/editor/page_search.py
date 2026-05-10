from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.page_binary_loading import (
    overlay_bytes,
)


class EditorPageSearchMixin:
    def find_text(self, mode: str, query: str) -> bool:
        results = self.find_offsets(mode, query)
        if results:
            self.go_to_offset(results[0])
            return True
        return False

    def find_offsets(self, mode: str, query: str) -> list[int]:
        if mode == BINARY_WORKBENCH_TEXT.FIND_HEX_BYTES:
            return self._find_hex_bytes(query)
        if mode == BINARY_WORKBENCH_TEXT.FIND_ASSEMBLY:
            return self._find_instruction(query)
        return []

    def _find_instruction(self, query: str) -> list[int]:
        needle = query.strip().lower()
        if not needle:
            return []
        rows = self.grid.export_rows() or self._context.rows
        return [
            int(row.offsets.get("File", "0x0"), 16)
            for row in rows
            if needle in row.instruction.lower()
        ]

    def _find_hex_bytes(self, query: str) -> list[int]:
        needle = hex_query_bytes(query)
        if not needle:
            return []
        if self._reader is None:
            return find_hex_in_rows(self._context.rows, needle)
        offset = 0
        carry = b""
        results: list[int] = []
        overlays = overlay_bytes(self._context.byte_overlays)
        while offset < self._reader.file_size:
            data = self._reader.read(offset, self._context.block_size, overlays)
            haystack = carry + data
            start = 0
            while (found := haystack.find(needle, start)) >= 0:
                results.append(max(0, offset - len(carry) + found))
                start = found + 1
            carry = haystack[-max(0, len(needle) - 1) :]
            offset += max(1, self._context.block_size)
        return results


def hex_query_bytes(value: str) -> bytes:
    try:
        return bytes.fromhex(value.replace(" ", ""))
    except ValueError:
        return b""


def find_hex_in_rows(rows: list, needle: bytes) -> list[int]:
    results: list[int] = []
    for row in rows:
        if needle.hex(" ").upper() in row.bytes_text:
            results.append(int(row.offsets.get("File", "0x0"), 16))
    return results
