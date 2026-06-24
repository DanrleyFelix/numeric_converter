from src.core.binary_workbench.text_search import (
    ansi_text_bytes,
    find_bytes_in_data,
    find_bytes_in_rows,
    find_hex_nibbles_in_data,
    find_hex_nibbles_in_rows,
    hex_nibbles,
)
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.page_overlays import (
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
        max_results: int | None = None,
    ) -> bool:
        results = self.find_offsets(mode, query, start_offset, end_offset, max_results)
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
        max_results: int | None = None,
    ) -> list[int]:
        if start_offset is not None and end_offset is not None and start_offset > end_offset:
            return []
        if mode == BINARY_WORKBENCH_TEXT.FIND_HEX_BYTES:
            return self._find_hex_bytes(query, start_offset, end_offset, max_results)
        if mode == BINARY_WORKBENCH_TEXT.FIND_ASSEMBLY:
            return self._find_instruction(query, start_offset, end_offset, max_results)
        if mode == BINARY_WORKBENCH_TEXT.FIND_DECODED_TEXT:
            return self._find_decoded_text(query, start_offset, end_offset, max_results)
        return []

    def _find_instruction(
        self,
        query: str,
        start_offset: int | None = None,
        end_offset: int | None = None,
        max_results: int | None = None,
    ) -> list[int]:
        instruction = query.strip()
        if not instruction:
            return []
        if self._reader is not None:
            return self._find_instruction_bytes(instruction, start_offset, end_offset, max_results)
        return self._find_instruction_rows(instruction, start_offset, end_offset, max_results)

    def _find_instruction_rows(
        self,
        query: str,
        start_offset: int | None = None,
        end_offset: int | None = None,
        max_results: int | None = None,
    ) -> list[int]:
        needle = query.lower()
        rows = self.grid.export_rows() or self._context.rows
        results: list[int] = []
        for row in rows:
            if row.offsets.get("File") == "-":
                continue
            offset = int(row.offsets.get("File", "0x0"), 16)
            if offset < (start_offset or 0) or (end_offset is not None and offset > end_offset):
                continue
            try:
                actual = bytes.fromhex(row.bytes_text.replace(" ", ""))
            except ValueError:
                actual = b""
            raw = _safe_disassemble(self.grid._codec, actual, offset) if actual else row.instruction.lower()
            if needle in raw:
                results.append(offset)
                if max_results is not None and len(results) >= max_results:
                    break
        return results

    def _find_instruction_bytes(
        self,
        query: str,
        start_offset: int | None = None,
        end_offset: int | None = None,
        max_results: int | None = None,
    ) -> list[int]:
        if self._reader is None:
            return []
        word_size = self.grid._codec.word_size
        offset = _align_offset(max(0, start_offset or 0), word_size)
        search_end = self._reader.file_size - 1 if end_offset is None else min(end_offset, self._reader.file_size - 1)
        if search_end - offset + 1 < word_size:
            return []
        overlays = overlay_bytes(self._context.byte_overlays)
        block_size = max(word_size, self._preferences.block_size)
        needle = query.lower()
        results: list[int] = []
        while offset + word_size - 1 <= search_end:
            read_size = min(block_size, search_end - offset + 1)
            data = self._reader.read(offset, read_size, overlays)
            for index in range(0, max(0, len(data) - word_size + 1), word_size):
                candidate_offset = offset + index
                raw = _safe_disassemble(self.grid._codec, data[index : index + word_size], candidate_offset)
                if needle in raw:
                    results.append(candidate_offset)
                    if max_results is not None and len(results) >= max_results:
                        return results
            offset += max(word_size, read_size - (read_size % word_size))
        return results

    def _find_hex_bytes(
        self,
        query: str,
        start_offset: int | None = None,
        end_offset: int | None = None,
        max_results: int | None = None,
    ) -> list[int]:
        needle = hex_nibbles(query)
        if not needle:
            return []
        return self._find_hex_nibbles(needle, start_offset, end_offset, max_results)

    def _find_decoded_text(
        self,
        query: str,
        start_offset: int | None = None,
        end_offset: int | None = None,
        max_results: int | None = None,
    ) -> list[int]:
        needle = ansi_text_bytes(query.strip())
        if not needle:
            return []
        return self._find_bytes(needle, start_offset, end_offset, max_results)

    def _find_bytes(
        self,
        needle: bytes,
        start_offset: int | None = None,
        end_offset: int | None = None,
        max_results: int | None = None,
    ) -> list[int]:
        if self._reader is None:
            return find_bytes_in_rows(self._context.rows, needle, start_offset, end_offset, max_results)
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
            remaining = None if max_results is None else max_results - len(results)
            results.extend(find_bytes_in_data(haystack, offset - len(carry), needle, start_offset, search_end, remaining))
            if max_results is not None and len(results) >= max_results:
                return results[:max_results]
            carry = haystack[-max(0, len(needle) - 1) :]
            offset += max(1, block_size)
        return results

    def _find_hex_nibbles(
        self,
        needle: str,
        start_offset: int | None = None,
        end_offset: int | None = None,
        max_results: int | None = None,
    ) -> list[int]:
        if self._reader is None:
            return find_hex_nibbles_in_rows(self._context.rows, needle, start_offset, end_offset, max_results)
        offset = max(0, start_offset or 0)
        search_end = self._reader.file_size - 1 if end_offset is None else min(end_offset, self._reader.file_size - 1)
        if search_end < offset:
            return []
        carry = b""
        results: list[int] = []
        overlays = overlay_bytes(self._context.byte_overlays)
        block_size = self._preferences.block_size
        carry_size = _hex_carry_size(needle)
        while offset <= search_end:
            data = self._reader.read(offset, min(block_size, search_end - offset + 1), overlays)
            haystack = carry + data
            for found in find_hex_nibbles_in_data(haystack, offset - len(carry), needle, start_offset, search_end):
                if found not in results:
                    results.append(found)
                    if max_results is not None and len(results) >= max_results:
                        return results[:max_results]
            if max_results is not None and len(results) >= max_results:
                return results[:max_results]
            carry = haystack[-carry_size:] if carry_size else b""
            offset += max(1, block_size)
        return results


def _hex_carry_size(needle: str) -> int:
    return max(0, ((len(needle) + 1) // 2))


def _align_offset(offset: int, word_size: int) -> int:
    remainder = offset % word_size
    return offset if remainder == 0 else offset + word_size - remainder


def _safe_disassemble(codec, data: bytes, offset: int) -> str:
    try:
        return codec.disassemble(data, offset).lower()
    except Exception:
        return ""
