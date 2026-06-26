from __future__ import annotations

from src.core.binary_workbench.masked_search import (
    MaskedBytePattern,
    find_masked_bytes_in_data,
)
from src.core.binary_workbench.mips_r3000a.instruction_patterns import (
    mips_instruction_byte_pattern,
)
from src.core.binary_workbench.text_search import (
    find_bytes_in_data,
    find_hex_nibbles_in_data,
)
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_FIND_MAX_LENGTH_BYTES,
)
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO


def find_reader_bytes(reader, overlays: dict[int, bytes], needle: bytes, start, end, limit, on_chunk=None) -> list[int]:
    if not needle:
        return []
    offset, search_end = _reader_range(reader, start, end)
    if search_end < offset:
        return []
    one_shot = _single_read(reader, overlays, offset, search_end)
    if one_shot is not None:
        return find_bytes_in_data(one_shot, offset, needle, start, search_end, limit)
    return []


def find_reader_hex(reader, overlays: dict[int, bytes], needle: str, start, end, limit, on_chunk=None) -> list[int]:
    offset, search_end = _reader_range(reader, start, end)
    if search_end < offset:
        return []
    one_shot = _single_read(reader, overlays, offset, search_end)
    if one_shot is not None:
        return find_hex_nibbles_in_data(one_shot, offset, needle, start, search_end, limit)
    return []


def find_reader_instruction(reader, codec, overlays, query: str, start, end, limit, on_chunk=None) -> list[int]:
    exact = codec.assemble(query, 0)
    if exact is not None and len(exact) == codec.word_size:
        return find_reader_masked(reader, overlays, MaskedBytePattern(exact, b"\xFF" * len(exact), codec.word_size), start, end, limit, on_chunk)
    pattern = mips_instruction_byte_pattern(query)
    if pattern is not None:
        return find_reader_masked(reader, overlays, pattern, start, end, limit, on_chunk)
    return _find_reader_disassembly(reader, codec, overlays, query, start, end, limit, on_chunk)


def find_reader_masked(reader, overlays: dict[int, bytes], pattern: MaskedBytePattern, start, end, limit, on_chunk=None) -> list[int]:
    offset, search_end = _reader_range(reader, start, end)
    if search_end < offset:
        return []
    one_shot = _single_read(reader, overlays, offset, search_end)
    if one_shot is not None:
        return find_masked_bytes_in_data(one_shot, offset, pattern, start, search_end, limit)
    return []


def effective_search_end(reader, rows: list[BinaryWorkbenchRowDTO], end_offset: int | None) -> int | None:
    if reader is not None:
        if reader.file_size <= 0:
            return None
        return min(end_offset if end_offset is not None else reader.file_size - 1, reader.file_size - 1)
    row_ends = [_row_end(row) for row in rows]
    row_ends = [value for value in row_ends if value is not None]
    return None if not row_ends else min(end_offset if end_offset is not None else max(row_ends), max(row_ends))


def _find_reader_disassembly(reader, codec, overlays, query, start, end, limit, on_chunk) -> list[int]:
    word_size = codec.word_size
    offset = _align(max(0, start or 0), word_size)
    search_end = _reader_range(reader, start, end)[1]
    if search_end - offset + 1 < word_size:
        return []
    one_shot = _single_read(reader, overlays, offset, search_end)
    data_chunks = [(offset, one_shot)] if one_shot is not None else []
    results: list[int] = []
    for base, data in data_chunks:
        for index in range(0, max(0, len(data) - word_size + 1), word_size):
            candidate = base + index
            if query.lower() in _safe_disassemble(codec, data[index:index + word_size], candidate):
                results.append(candidate)
                if limit is not None and len(results) >= limit:
                    return results
    return results


def _single_read(reader, overlays, offset: int, search_end: int) -> bytes | None:
    size = search_end - offset + 1
    if size <= 0 or size > BINARY_WORKBENCH_FIND_MAX_LENGTH_BYTES:
        return None
    return reader.read_uncached(offset, size, overlays)


def _reader_range(reader, start, end) -> tuple[int, int]:
    offset = max(0, start or 0)
    requested_end = reader.file_size - 1 if end is None else min(end, reader.file_size - 1)
    search_end = min(requested_end, offset + BINARY_WORKBENCH_FIND_MAX_LENGTH_BYTES - 1)
    return offset, search_end


def _row_end(row: BinaryWorkbenchRowDTO) -> int | None:
    try:
        offset = int(row.offsets.get("File", ""), 16)
    except ValueError:
        return None
    return offset + max(0, len(row.bytes_text.replace(" ", "")) // 2) - 1


def _align(offset: int, word_size: int) -> int:
    remainder = offset % word_size
    return offset if remainder == 0 else offset + word_size - remainder


def _safe_disassemble(codec, data: bytes, offset: int) -> str:
    try:
        return codec.disassemble(data, offset).lower()
    except Exception:
        return ""
