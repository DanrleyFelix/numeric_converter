from src.core.converter.converter import Converter
from src.core.converter.errors import ConverterValidationError
from src.modules.binary_workbench_constants import ANSI_WINDOWS_ENCODING as ANSI_TEXT_ENCODING
from src.modules.constants import HEX_DIGITS_LOWER
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO


def ansi_text_bytes(text: str) -> bytes:
    try:
        return text.encode(ANSI_TEXT_ENCODING)
    except UnicodeEncodeError:
        return b""


def find_bytes_in_data(
    data: bytes,
    base_offset: int,
    needle: bytes,
    start_offset: int | None = None,
    end_offset: int | None = None,
    max_results: int | None = None,
) -> list[int]:
    if not needle:
        return []
    left = max(0, (start_offset or 0) - base_offset)
    right = len(data) if end_offset is None else min(len(data), end_offset - base_offset + 1)
    if right < left or (end_offset is not None and start_offset is not None and start_offset > end_offset):
        return []
    results: list[int] = []
    haystack = data[left:right]
    start = 0
    while (found := haystack.find(needle, start)) >= 0:
        results.append(base_offset + left + found)
        if max_results is not None and len(results) >= max_results:
            break
        start = found + 1
    return results


def find_bytes_in_rows(
    rows: list[BinaryWorkbenchRowDTO],
    needle: bytes,
    start_offset: int | None = None,
    end_offset: int | None = None,
    max_results: int | None = None,
) -> list[int]:
    if not needle:
        return []
    chunks = sorted(_row_chunks(rows), key=lambda item: item[0])
    results: list[int] = []
    run_offset: int | None = None
    run_data = bytearray()
    for offset, data in chunks:
        if run_offset is None:
            run_offset = offset
        if offset != run_offset + len(run_data):
            remaining = None if max_results is None else max_results - len(results)
            results.extend(find_bytes_in_data(bytes(run_data), run_offset, needle, start_offset, end_offset, remaining))
            if max_results is not None and len(results) >= max_results:
                return results[:max_results]
            run_offset = offset
            run_data = bytearray()
        run_data.extend(data)
    if run_offset is not None:
        remaining = None if max_results is None else max_results - len(results)
        results.extend(find_bytes_in_data(bytes(run_data), run_offset, needle, start_offset, end_offset, remaining))
    return results[:max_results] if max_results is not None else results


def find_hex_nibbles_in_data(
    data: bytes,
    base_offset: int,
    query: str,
    start_offset: int | None = None,
    end_offset: int | None = None,
    max_results: int | None = None,
) -> list[int]:
    needle = hex_nibbles(query)
    if not needle:
        return []
    left = max(0, (start_offset or 0) - base_offset)
    right = len(data) if end_offset is None else min(len(data), end_offset - base_offset + 1)
    if right < left or (end_offset is not None and start_offset is not None and start_offset > end_offset):
        return []
    haystack = data[left:right].hex()
    results: list[int] = []
    seen: set[int] = set()
    start = 0
    while (found := haystack.find(needle, start)) >= 0:
        offset = base_offset + left + (found // 2)
        if offset not in seen:
            results.append(offset)
            seen.add(offset)
            if max_results is not None and len(results) >= max_results:
                break
        start = found + 1
    return results


def find_hex_nibbles_in_rows(
    rows: list[BinaryWorkbenchRowDTO],
    query: str,
    start_offset: int | None = None,
    end_offset: int | None = None,
    max_results: int | None = None,
) -> list[int]:
    if not hex_nibbles(query):
        return []
    chunks = sorted(_row_chunks(rows), key=lambda item: item[0])
    results: list[int] = []
    run_offset: int | None = None
    run_data = bytearray()
    for offset, data in chunks:
        if run_offset is None:
            run_offset = offset
        if offset != run_offset + len(run_data):
            remaining = None if max_results is None else max_results - len(results)
            results.extend(find_hex_nibbles_in_data(bytes(run_data), run_offset, query, start_offset, end_offset, remaining))
            if max_results is not None and len(results) >= max_results:
                return results[:max_results]
            run_offset = offset
            run_data = bytearray()
        run_data.extend(data)
    if run_offset is not None:
        remaining = None if max_results is None else max_results - len(results)
        results.extend(find_hex_nibbles_in_data(bytes(run_data), run_offset, query, start_offset, end_offset, remaining))
    return results[:max_results] if max_results is not None else results


def hex_nibbles(value: str) -> str:
    clean = "".join(character for character in value.lower() if not character.isspace())
    return clean if clean and all(character in HEX_DIGITS_LOWER for character in clean) else ""


def big_endian_hex_to_little_endian_nibbles(value: str) -> str:
    clean = hex_nibbles(value)
    if not clean:
        return ""
    try:
        return Converter.convert("hexBE", clean)["hexLE"].hex()
    except ConverterValidationError:
        return ""


def _row_chunks(rows: list[BinaryWorkbenchRowDTO]) -> list[tuple[int, bytes]]:
    chunks: list[tuple[int, bytes]] = []
    for row in rows:
        offset_text = row.offsets.get("File", "-")
        if offset_text == "-":
            continue
        try:
            chunks.append((int(offset_text, 16), bytes.fromhex(row.bytes_text.replace(" ", ""))))
        except ValueError:
            continue
    return chunks
