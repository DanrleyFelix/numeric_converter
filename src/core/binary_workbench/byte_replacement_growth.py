from src.core.binary_workbench.byte_replacement import (
    bytes_from_rows,
    replaced_row_byte_lines,
)
from src.modules.binary_workbench_constants import BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO


def replaced_or_extended_row_byte_lines(
    rows: list[BinaryWorkbenchRowDTO],
    start: int,
    replacement: bytes,
    allow_extension: bool,
) -> list[str] | None:
    """Replace covered bytes and optionally append bytes beyond the current end."""

    file_end = _file_end(rows)
    if start < 0 or start > file_end or not replacement:
        return None
    covered_size = min(len(replacement), file_end - start)
    if covered_size and bytes_from_rows(rows, start, covered_size) is None:
        return None
    if covered_size:
        lines = replaced_row_byte_lines(rows, start, replacement[:covered_size])
        if lines is None:
            return None
    else:
        lines = [row.bytes_text for row in rows]
    extension = replacement[covered_size:]
    if not extension:
        return lines
    if not allow_extension:
        return None
    return _append_bytes(rows, lines, file_end, extension)


def _append_bytes(
    rows: list[BinaryWorkbenchRowDTO],
    lines: list[str],
    file_end: int,
    extension: bytes,
) -> list[str]:
    """Append bytes to a partial final row and then create new byte rows."""

    last_index = _last_data_row_index(rows, file_end)
    remaining = extension
    if last_index is not None:
        current = bytes.fromhex(lines[last_index])
        room = max(0, ROW_BYTES - len(current))
        if room:
            current += remaining[:room]
            remaining = remaining[room:]
            lines[last_index] = _bytes_text(current)
    lines.extend(_bytes_text(remaining[index : index + ROW_BYTES]) for index in range(0, len(remaining), ROW_BYTES))
    return lines


def _file_end(rows: list[BinaryWorkbenchRowDTO]) -> int:
    """Return the greatest byte end represented by valid rows."""

    ends = []
    for row in rows:
        try:
            ends.append(int(row.offsets.get("File", "-"), 16) + len(bytes.fromhex(row.bytes_text)))
        except ValueError:
            continue
    return max(ends, default=0)


def _last_data_row_index(rows: list[BinaryWorkbenchRowDTO], file_end: int) -> int | None:
    """Locate the valid row whose bytes currently reach the file end."""

    for index in range(len(rows) - 1, -1, -1):
        row = rows[index]
        try:
            offset = int(row.offsets.get("File", "-"), 16)
            if offset + len(bytes.fromhex(row.bytes_text)) == file_end:
                return index
        except ValueError:
            continue
    return None


def _bytes_text(data: bytes) -> str:
    """Format bytes using the editor's canonical spacing."""

    return " ".join(f"{value:02X}" for value in data)
