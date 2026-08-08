from __future__ import annotations

from src.core.binary_workbench.hazard_cache import HazardCacheItem
from src.core.binary_workbench.mips_r3000a import validate_mips_hazards
from src.modules.binary_workbench_constants import (
    BINARY_WORKBENCH_ROW_BYTES as ROW_BYTES,
)
from src.modules.binary_workbench_dtos import BinaryWorkbenchRowDTO


def hazard_items_from_rows(
    rows: list[BinaryWorkbenchRowDTO],
    start_offset: int | None = None,
    end_offset: int | None = None,
) -> list[HazardCacheItem]:
    instructions = [row.instruction for row in rows]
    hazards = validate_mips_hazards(instructions)
    return [
        HazardCacheItem(
            offset=offset,
            instruction=rows[item.line_index].instruction.strip(),
            severity=item.severity,
            message=item.message,
        )
        for item in hazards
        if item.line_index < len(rows)
        and (offset := _row_offset(rows[item.line_index])) is not None
        and _offset_in_range(offset, start_offset, end_offset)
    ]


def hazard_items_from_reader(
    reader,
    codec,
    overlays: dict[int, bytes],
    start_offset: int | None,
    end_offset: int | None,
    instruction_overlays: dict[str, str] | None = None,
) -> list[HazardCacheItem]:
    word_size = max(1, codec.word_size)
    scan_start, scan_end = _scan_range(reader.file_size, word_size, start_offset, end_offset)
    if scan_end < scan_start:
        return []
    data = reader.read_uncached(scan_start, scan_end - scan_start + 1, overlays)
    instructions: list[str] = []
    offsets: list[int] = []
    for index in range(0, max(0, len(data) - word_size + 1), word_size):
        offset = scan_start + index
        instructions.append(
            _instruction_for_offset(
                codec,
                data[index:index + word_size],
                offset,
                instruction_overlays or {},
            )
        )
        offsets.append(offset)
    hazards = validate_mips_hazards(instructions)
    return [
        HazardCacheItem(
            offset=offset,
            instruction=instructions[item.line_index],
            severity=item.severity,
            message=item.message,
        )
        for item in hazards
        if item.line_index < len(offsets)
        and _offset_in_range((offset := offsets[item.line_index]), start_offset, end_offset)
    ]


def _scan_range(
    file_size: int,
    word_size: int,
    start_offset: int | None,
    end_offset: int | None,
) -> tuple[int, int]:
    if file_size <= 0:
        return 0, -1
    start = _align_down(max(0, start_offset or 0), word_size)
    if start > 0:
        start = max(0, start - word_size)
    requested_end = file_size - 1 if end_offset is None else min(end_offset, file_size - 1)
    end = min(file_size - 1, _align_down(requested_end, word_size) + word_size - 1)
    return start, end


def _row_offset(row: BinaryWorkbenchRowDTO) -> int | None:
    try:
        return int(row.offsets.get("File", ""), 16)
    except ValueError:
        return None


def _offset_in_range(offset: int, start_offset: int | None, end_offset: int | None) -> bool:
    if start_offset is not None and offset < start_offset:
        return False
    if end_offset is not None and offset > end_offset:
        return False
    return True


def _align_down(offset: int, word_size: int) -> int:
    return offset - (offset % word_size)


def _instruction_for_offset(codec, data: bytes, offset: int, instruction_overlays: dict[str, str]) -> str:
    overlay = instruction_overlays.get(f"0x{offset:08X}")
    if overlay is not None:
        return overlay.strip()
    return _safe_disassemble(codec, data, offset)


def _safe_disassemble(codec, data: bytes, offset: int) -> str:
    try:
        return codec.disassemble(data.ljust(ROW_BYTES, b"\x00"), offset)
    except Exception:
        return ""
