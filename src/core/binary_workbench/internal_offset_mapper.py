from __future__ import annotations

from dataclasses import dataclass

from src.core.binary_workbench.internal_file_region import InternalFileRegion
from src.core.binary_workbench.psx_sector_layout import (
    SECTOR_LAYOUT_PREFIX_SIZE,
    PsxSectorLayout,
    sector_layout,
)


@dataclass(frozen=True)
class InternalToBinaryChunk:
    internal_offset: int
    binary_offset: int
    size: int
    sector_index: int


@dataclass(frozen=True)
class _SectorSpan:
    internal_start: int
    binary_start: int
    data_size: int
    sector_index: int
    layout: PsxSectorLayout

    @property
    def internal_end(self) -> int:
        return self.internal_start + self.data_size


class InternalOffsetMapper:
    def __init__(self, region: InternalFileRegion) -> None:
        self.region = region
        self._spans: list[_SectorSpan] = []
        self._complete = region.sector_count == 0
        self._source_size = region.source_path.stat().st_size if region.source_path.exists() else 0

    @property
    def estimated_size(self) -> int:
        if self._complete:
            return self.logical_size
        first = self._ensure_sector(0)
        size = first.data_size if first is not None else 0
        return self.region.sector_count * size

    @property
    def logical_size(self) -> int:
        return self._spans[-1].internal_end if self._spans else 0

    @property
    def complete(self) -> bool:
        return self._complete

    @property
    def cached_sector_count(self) -> int:
        return len(self._spans)

    def binary_offset_for_internal(self, internal_offset: int) -> int | None:
        chunks = self.chunks_for_internal_range(internal_offset, 1)
        return chunks[0].binary_offset if chunks else None

    def chunks_for_internal_range(
        self,
        internal_offset: int,
        size: int,
    ) -> list[InternalToBinaryChunk]:
        if internal_offset < 0 or size <= 0:
            return []
        chunks: list[InternalToBinaryChunk] = []
        cursor = internal_offset
        remaining = size
        span = self._span_for_internal_offset(cursor)
        while span is not None and remaining > 0:
            relative = cursor - span.internal_start
            take = min(remaining, span.data_size - relative)
            chunks.append(InternalToBinaryChunk(
                internal_offset=cursor,
                binary_offset=span.binary_start + relative,
                size=take,
                sector_index=span.sector_index,
            ))
            cursor += take
            remaining -= take
            span = self._span_for_internal_offset(cursor) if remaining else None
        return chunks

    def chunks_for_binary_range(
        self,
        binary_offset: int,
        size: int,
    ) -> list[InternalToBinaryChunk]:
        if binary_offset < 0 or size <= 0:
            return []
        binary_end = binary_offset + size
        first_sector = max(
            0,
            (binary_offset // self.region.sector_size) - self.region.start_lba,
        )
        last_sector = min(
            self.region.sector_count - 1,
            ((binary_end - 1) // self.region.sector_size) - self.region.start_lba,
        )
        chunks: list[InternalToBinaryChunk] = []
        for relative_sector in range(first_sector, last_sector + 1):
            span = self._ensure_sector(relative_sector)
            if span is None:
                break
            left = max(binary_offset, span.binary_start)
            right = min(binary_end, span.binary_start + span.data_size)
            if left >= right:
                continue
            chunks.append(InternalToBinaryChunk(
                internal_offset=span.internal_start + (left - span.binary_start),
                binary_offset=left,
                size=right - left,
                sector_index=span.sector_index,
            ))
        return chunks

    def _span_for_internal_offset(self, offset: int) -> _SectorSpan | None:
        for span in self._spans:
            if span.internal_start <= offset < span.internal_end:
                return span
        with self.region.source_path.open("rb") as source:
            while not self._complete and (not self._spans or offset >= self._spans[-1].internal_end):
                if self._append_next_sector(source) is None:
                    break
                if offset < self._spans[-1].internal_end:
                    return self._spans[-1]
        return None

    def _ensure_sector(self, relative_sector: int) -> _SectorSpan | None:
        with self.region.source_path.open("rb") as source:
            while len(self._spans) <= relative_sector and not self._complete:
                if self._append_next_sector(source) is None:
                    break
        return self._spans[relative_sector] if relative_sector < len(self._spans) else None

    def _append_next_sector(self, source) -> _SectorSpan | None:
        relative_sector = len(self._spans)
        if relative_sector >= self.region.sector_count:
            self._complete = True
            return None
        sector_index = self.region.start_lba + relative_sector
        sector_start = sector_index * self.region.sector_size
        available = min(self.region.sector_size, max(0, self._source_size - sector_start))
        source.seek(sector_start)
        prefix = source.read(min(SECTOR_LAYOUT_PREFIX_SIZE, available))
        layout = sector_layout(prefix, self.region.sector_size, available)
        data_size = min(layout.data_size, max(0, available - layout.data_offset))
        internal_start = self._spans[-1].internal_end if self._spans else 0
        span = _SectorSpan(
            internal_start,
            sector_start + layout.data_offset,
            data_size,
            sector_index,
            layout,
        )
        self._spans.append(span)
        if len(self._spans) >= self.region.sector_count:
            self._complete = True
        return span
