from __future__ import annotations

from src.core.binary_workbench.masked_search import (
    MaskedBytePattern,
    find_masked_bytes_in_data,
)
from src.core.binary_workbench.mips_r3000a.instruction_patterns import (
    mips_instruction_byte_pattern,
)
from src.core.binary_workbench.text_search import (
    ansi_text_bytes,
    find_hex_nibbles_in_data,
    hex_nibbles,
)


def offset_matches_bytes(read_bytes, needle: bytes, offset: int) -> bool:
    return bool(needle) and read_bytes(offset, len(needle)) == needle


def offset_matches_hex(read_bytes, query: str, offset: int) -> bool:
    needle = hex_nibbles(query)
    if not needle:
        return False
    size = max(0, (len(needle) + 1) // 2)
    data = read_bytes(offset, size)
    return find_hex_nibbles_in_data(data, offset, needle, offset, offset + len(data) - 1, 1) == [offset]


def offset_matches_decoded_text(read_bytes, query: str, offset: int) -> bool:
    return offset_matches_bytes(read_bytes, ansi_text_bytes(query.strip()), offset)


def offset_matches_instruction(read_bytes, codec, query: str, offset: int) -> bool:
    exact = codec.assemble(query, 0)
    if exact is not None and len(exact) == codec.word_size:
        return offset_matches_bytes(read_bytes, exact, offset)
    pattern = mips_instruction_byte_pattern(query)
    if pattern is not None:
        return _offset_matches_masked(read_bytes, pattern, offset)
    data = read_bytes(offset, codec.word_size)
    return query.lower() in _safe_disassemble(codec, data, offset)


def _offset_matches_masked(read_bytes, pattern: MaskedBytePattern, offset: int) -> bool:
    data = read_bytes(offset, len(pattern.needle))
    return find_masked_bytes_in_data(data, offset, pattern, offset, offset + len(data) - 1, 1) == [offset]


def _safe_disassemble(codec, data: bytes, offset: int) -> str:
    try:
        return codec.disassemble(data, offset).lower()
    except Exception:
        return ""
