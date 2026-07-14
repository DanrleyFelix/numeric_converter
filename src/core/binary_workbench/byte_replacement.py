from __future__ import annotations

from dataclasses import dataclass

from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO


@dataclass(frozen=True)
class ReplaceBytesRequest:
    """Validated byte replacement parameters collected by the Search dialog."""

    start_offset: int
    data: bytes
    end_offset: int | None = None
    length_limit: int | None = None


def parse_replace_bytes_request(
    start_text: str,
    end_text: str,
    length_text: str,
    bytes_text: str,
) -> ReplaceBytesRequest | None:
    """Parse and validate replacement offsets, limits, and hexadecimal bytes."""

    try:
        start = int(start_text.strip(), 16)
        end = int(end_text.strip(), 16) if end_text.strip() else None
        length = _integer_or_hex(length_text) if length_text.strip() else None
        data = bytes.fromhex(bytes_text)
    except ValueError:
        return None
    if start < 0 or not data or end is not None and end < start or length is not None and length < 0:
        return None
    if length is not None and len(data) > length:
        return None
    if end is not None and start + len(data) - 1 > end:
        return None
    return ReplaceBytesRequest(start, data, end, length)


def bytes_from_rows(
    rows: list[BinaryWorkbenchRowDTO],
    start: int,
    size: int,
) -> bytes | None:
    """Read an exact byte range from offset-bearing rows, ignoring comment rows."""

    if start < 0 or size < 0:
        return None
    if size == 0:
        return b""
    data = bytearray(size)
    covered = bytearray(size)
    for row in rows:
        parsed = _row_data(row)
        if parsed is None:
            continue
        offset, row_data = parsed
        left, right = max(start, offset), min(start + size, offset + len(row_data))
        if left >= right:
            continue
        data[left - start : right - start] = row_data[left - offset : right - offset]
        covered[left - start : right - start] = b"\x01" * (right - left)
    return bytes(data) if all(covered) else None


def replaced_row_byte_lines(
    rows: list[BinaryWorkbenchRowDTO],
    start: int,
    replacement: bytes,
) -> list[str] | None:
    """Return row-aligned byte lines with one exact range replaced."""

    if not replacement or bytes_from_rows(rows, start, len(replacement)) is None:
        return None
    end = start + len(replacement)
    lines: list[str] = []
    for row in rows:
        parsed = _row_data(row)
        if parsed is None:
            lines.append("")
            continue
        offset, row_data = parsed
        updated = bytearray(row_data)
        left, right = max(start, offset), min(end, offset + len(updated))
        if left < right:
            updated[left - offset : right - offset] = replacement[left - start : right - start]
        lines.append(_bytes_text(bytes(updated)))
    return lines


def merged_byte_overlays(
    overlays: dict[str, str],
    start: int,
    replacement: bytes,
) -> dict[str, str]:
    """Merge a byte range into overlays without leaving overlapping patches."""

    end = start + len(replacement)
    segments: list[tuple[int, bytes]] = []
    for offset_text, bytes_text in overlays.items():
        try:
            offset, data = int(offset_text, 16), bytes.fromhex(bytes_text)
        except ValueError:
            continue
        patch_end = offset + len(data)
        if patch_end <= start or offset >= end:
            segments.append((offset, data))
            continue
        if offset < start:
            segments.append((offset, data[: start - offset]))
        if patch_end > end:
            segments.append((end, data[end - offset :]))
    segments.append((start, replacement))
    return {f"0x{offset:08X}": _bytes_text(data) for offset, data in sorted(segments)}


def without_overlapping_instructions(
    overlays: dict[str, str],
    start: int,
    size: int,
    word_size: int = 4,
) -> dict[str, str]:
    """Remove instruction overlays whose machine word overlaps replaced bytes."""

    end = start + size
    retained: dict[str, str] = {}
    for offset_text, instruction in overlays.items():
        try:
            offset = int(offset_text, 16)
        except ValueError:
            continue
        if offset >= end or offset + word_size <= start:
            retained[offset_text] = instruction
    return retained


def _row_data(row: BinaryWorkbenchRowDTO) -> tuple[int, bytes] | None:
    """Parse one row with a real file offset and byte payload."""

    try:
        offset = int(row.offsets.get("File", "-"), 16)
        return offset, bytes.fromhex(row.bytes_text)
    except ValueError:
        return None


def _integer_or_hex(text: str) -> int:
    """Parse decimal by default and hexadecimal when prefixed with 0x."""

    value = text.strip()
    return int(value, 16 if value.lower().startswith("0x") else 10)


def _bytes_text(data: bytes) -> str:
    """Format bytes using the Binary Workbench canonical representation."""

    return " ".join(f"{value:02X}" for value in data)
