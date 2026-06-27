from PySide6.QtCore import QCoreApplication

from src.core.binary_workbench.searching import (
    effective_search_end,
    find_reader_bytes,
    find_reader_hex,
    find_reader_instruction,
    offset_matches_decoded_text,
    offset_matches_hex,
    offset_matches_instruction,
)
from src.core.binary_workbench.text_search import (
    ansi_text_bytes,
    big_endian_hex_to_little_endian_nibbles,
    find_bytes_in_rows,
    find_hex_nibbles_in_rows,
    hex_nibbles,
)
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_SEARCH_EVENT_CHUNKS
from src.presentation.ui.components.binary_workbench.constants import BINARY_WORKBENCH_TEXT
from src.presentation.ui.components.binary_workbench.editor.page_overlays import overlay_bytes


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

    def find_text(self, mode: str, query: str, start_offset=None, end_offset=None, max_results=None) -> bool:
        results = self.find_offsets(mode, query, start_offset, end_offset, max_results)
        if results:
            self.go_to_offset(results[0])
            return True
        return False

    def find_offsets(self, mode: str, query: str, start_offset=None, end_offset=None, max_results=None) -> list[int]:
        if start_offset is not None and end_offset is not None and start_offset > end_offset:
            return []
        self.remember_search_end_offset(start_offset, end_offset)
        if mode in {
            BINARY_WORKBENCH_TEXT.FIND_HEX_BYTES,
            BINARY_WORKBENCH_TEXT.FIND_HEX_BYTES_BE,
        }:
            return self._find_hex_bytes(mode, query, start_offset, end_offset, max_results)
        if mode == BINARY_WORKBENCH_TEXT.FIND_ASSEMBLY:
            return self._find_instruction(query, start_offset, end_offset, max_results)
        if mode == BINARY_WORKBENCH_TEXT.FIND_DECODED_TEXT:
            return self._find_decoded_text(query, start_offset, end_offset, max_results)
        return []

    def last_search_end_offset(self) -> int | None:
        return getattr(self, "_last_search_end_offset", None)

    def remember_search_end_offset(self, start_offset: int | None, end_offset: int | None) -> None:
        search_end = effective_search_end(self._reader, self._context.rows, end_offset)
        file_end = effective_search_end(self._reader, self._context.rows, None)
        self._last_search_end_offset = None if search_end is not None and search_end == file_end else search_end

    def search_offset_matches(self, mode: str, query: str, offset: int) -> bool:
        if mode in {
            BINARY_WORKBENCH_TEXT.FIND_HEX_BYTES,
            BINARY_WORKBENCH_TEXT.FIND_HEX_BYTES_BE,
        }:
            return offset_matches_hex(self._read_match_bytes, self._hex_query_for_mode(mode, query), offset)
        if mode == BINARY_WORKBENCH_TEXT.FIND_DECODED_TEXT:
            return offset_matches_decoded_text(self._read_match_bytes, query, offset)
        if mode == BINARY_WORKBENCH_TEXT.FIND_ASSEMBLY:
            return offset_matches_instruction(self._read_match_bytes, self.grid._codec, query.strip(), offset)
        return False

    def _find_instruction(self, query: str, start_offset=None, end_offset=None, max_results=None) -> list[int]:
        instruction = query.strip()
        if not instruction:
            return []
        if self._reader is not None:
            return find_reader_instruction(
                self._reader,
                self.grid._codec,
                overlay_bytes(self._context.byte_overlays),
                instruction,
                start_offset,
                end_offset,
                max_results,
                self._yield_search_events,
            )
        return self._find_instruction_rows(instruction, start_offset, end_offset, max_results)

    def _find_instruction_rows(self, query: str, start_offset=None, end_offset=None, max_results=None) -> list[int]:
        needle = query.lower()
        results: list[int] = []
        for row in self.grid.export_rows() or self._context.rows:
            offset_text = row.offsets.get(BINARY_WORKBENCH_TEXT.FILE, "-")
            if offset_text == "-":
                continue
            offset = int(offset_text, 16)
            if offset < (start_offset or 0) or (end_offset is not None and offset > end_offset):
                continue
            if needle in row.instruction.lower():
                results.append(offset)
                if max_results is not None and len(results) >= max_results:
                    break
        return results

    def _find_hex_bytes(self, mode: str, query: str, start_offset=None, end_offset=None, max_results=None) -> list[int]:
        needle = self._hex_query_for_mode(mode, query)
        if not needle:
            return []
        if self._reader is None:
            return find_hex_nibbles_in_rows(self._context.rows, needle, start_offset, end_offset, max_results)
        return find_reader_hex(self._reader, overlay_bytes(self._context.byte_overlays), needle, start_offset, end_offset, max_results, self._yield_search_events)

    def _hex_query_for_mode(self, mode: str, query: str) -> str:
        if mode == BINARY_WORKBENCH_TEXT.FIND_HEX_BYTES_BE:
            return big_endian_hex_to_little_endian_nibbles(query)
        return hex_nibbles(query)

    def _find_decoded_text(self, query: str, start_offset=None, end_offset=None, max_results=None) -> list[int]:
        needle = ansi_text_bytes(query.strip())
        if not needle:
            return []
        if self._reader is None:
            return find_bytes_in_rows(self._context.rows, needle, start_offset, end_offset, max_results)
        return find_reader_bytes(self._reader, overlay_bytes(self._context.byte_overlays), needle, start_offset, end_offset, max_results, self._yield_search_events)

    def _read_match_bytes(self, offset: int, size: int) -> bytes:
        if self._reader is None:
            for row in self._context.rows:
                if row.offsets.get(BINARY_WORKBENCH_TEXT.FILE) == f"0x{offset:08X}":
                    return bytes.fromhex(row.bytes_text.replace(" ", ""))
            return b""
        return self._reader.read_uncached(offset, size, overlay_bytes(self._context.byte_overlays))

    def _yield_search_events(self) -> None:
        count = getattr(self, "_search_event_chunks", 0) + 1
        self._search_event_chunks = count
        if count % BINARY_WORKBENCH_SEARCH_EVENT_CHUNKS == 0:
            app = QCoreApplication.instance()
            if app is not None:
                app.processEvents()
