from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.modules.binary_workbench_dtos import BinaryWorkbenchInternalFileDTO

RAW_SECTOR_SIZE = 2352
SYNC_HEADER = b"\x00" + (b"\xFF" * 10) + b"\x00"


@dataclass(frozen=True)
class PsxSectorLayout:
    data_offset: int
    data_size: int
    mode: int = 0
    form: int = 0


@dataclass(frozen=True)
class InternalFileSpan:
    internal_start: int
    binary_start: int
    size: int


def sector_layout(sector: bytes, sector_size: int) -> PsxSectorLayout:
    if sector_size != RAW_SECTOR_SIZE or len(sector) < RAW_SECTOR_SIZE:
        return PsxSectorLayout(0, len(sector))
    if sector[: len(SYNC_HEADER)] != SYNC_HEADER:
        return PsxSectorLayout(24, 2048)
    mode = sector[15]
    if mode == 1:
        return PsxSectorLayout(16, 2048, mode=1, form=1)
    if mode != 2:
        return PsxSectorLayout(0, len(sector))
    form = 2 if sector[18] & 0x20 else 1
    return PsxSectorLayout(24, 2324 if form == 2 else 2048, mode=2, form=form)


def internal_file_spans(
    source_path: Path,
    target: BinaryWorkbenchInternalFileDTO,
    internal_files: list[BinaryWorkbenchInternalFileDTO],
    sector_size: int,
) -> list[InternalFileSpan]:
    if sector_size <= 0 or target.start_lba < 0:
        return []
    source_size = source_path.stat().st_size
    sector_count = (source_size + sector_size - 1) // sector_size
    end_lba = next(
        (
            item.start_lba
            for item in sorted(internal_files, key=lambda item: item.start_lba)
            if item.start_lba > target.start_lba
        ),
        sector_count,
    )
    internal_start = 0
    spans: list[InternalFileSpan] = []
    with source_path.open("rb") as source:
        for lba in range(target.start_lba, min(end_lba, sector_count)):
            sector_start = lba * sector_size
            source.seek(sector_start)
            sector = source.read(min(sector_size, source_size - sector_start))
            layout = sector_layout(sector, sector_size)
            size = min(layout.data_size, max(0, len(sector) - layout.data_offset))
            if size <= 0:
                continue
            spans.append(InternalFileSpan(internal_start, sector_start + layout.data_offset, size))
            internal_start += size
    return spans


def extract_internal_file_bytes(
    source_path: Path,
    target: BinaryWorkbenchInternalFileDTO,
    internal_files: list[BinaryWorkbenchInternalFileDTO],
    sector_size: int,
) -> bytes:
    payload = bytearray()
    with source_path.open("rb") as source:
        for span in internal_file_spans(source_path, target, internal_files, sector_size):
            source.seek(span.binary_start)
            payload.extend(source.read(span.size))
    return bytes(payload)


def binary_offset_for_internal(
    spans: list[InternalFileSpan],
    internal_offset: int,
) -> int | None:
    for span in spans:
        relative = internal_offset - span.internal_start
        if 0 <= relative < span.size:
            return span.binary_start + relative
    return None
