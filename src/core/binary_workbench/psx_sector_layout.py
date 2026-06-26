from __future__ import annotations

from dataclasses import dataclass

RAW_SECTOR_SIZE = 2352
SECTOR_LAYOUT_PREFIX_SIZE = 24
SYNC_HEADER = b"\x00" + (b"\xFF" * 10) + b"\x00"


@dataclass(frozen=True)
class PsxSectorLayout:
    data_offset: int
    data_size: int
    mode: int = 0
    form: int = 0


def sector_layout(
    sector_prefix: bytes,
    sector_size: int,
    available_size: int | None = None,
) -> PsxSectorLayout:
    available = len(sector_prefix) if available_size is None else max(0, available_size)
    if sector_size != RAW_SECTOR_SIZE:
        return PsxSectorLayout(0, min(max(0, sector_size), available))
    if available < RAW_SECTOR_SIZE or len(sector_prefix) < SECTOR_LAYOUT_PREFIX_SIZE:
        return PsxSectorLayout(0, 0)
    if sector_prefix[: len(SYNC_HEADER)] != SYNC_HEADER:
        return PsxSectorLayout(0, 0)
    mode = sector_prefix[15]
    if mode == 1:
        return PsxSectorLayout(16, 2048, mode=1, form=1)
    if mode != 2:
        return PsxSectorLayout(0, 0)
    form = 2 if sector_prefix[18] & 0x20 else 1
    return PsxSectorLayout(24, 2324 if form == 2 else 2048, mode=2, form=form)
