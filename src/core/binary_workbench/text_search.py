from src.modules.dtos import BinaryWorkbenchRowDTO


ANSI_TEXT_ENCODING = "cp1252"


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
        start = found + 1
    return results


def find_bytes_in_rows(
    rows: list[BinaryWorkbenchRowDTO],
    needle: bytes,
    start_offset: int | None = None,
    end_offset: int | None = None,
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
            results.extend(find_bytes_in_data(bytes(run_data), run_offset, needle, start_offset, end_offset))
            run_offset = offset
            run_data = bytearray()
        run_data.extend(data)
    if run_offset is not None:
        results.extend(find_bytes_in_data(bytes(run_data), run_offset, needle, start_offset, end_offset))
    return results


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
