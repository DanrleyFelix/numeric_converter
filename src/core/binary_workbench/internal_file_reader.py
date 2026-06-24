from __future__ import annotations

from src.core.binary_workbench.block_reader import BinaryBlock, BinaryBlockCache
from src.core.binary_workbench.internal_file_region import InternalFileRegion
from src.core.binary_workbench.internal_offset_mapper import InternalOffsetMapper

INTERNAL_FILE_EXPORT_CHUNK_SIZE = 1024 * 1024


class InternalFileView:
    def __init__(self, region: InternalFileRegion, block_size: int, cache_max_blocks: int) -> None:
        self.region = region
        self.block_size = max(1, block_size)
        self.mapper = InternalOffsetMapper(region)
        self.cache = BinaryBlockCache(cache_max_blocks)

    @property
    def file_size(self) -> int:
        return self.mapper.logical_size if self.mapper.complete else self.mapper.estimated_size

    def block_index_for_offset(self, offset: int) -> int:
        return max(0, offset) // self.block_size

    def binary_offset_for_internal(self, offset: int) -> int | None:
        return self.mapper.binary_offset_for_internal(offset)

    def read(
        self,
        offset: int,
        size: int,
        overlay: dict[int, bytes] | None = None,
    ) -> bytes:
        if size <= 0 or offset >= self.file_size:
            return b""
        start = max(0, offset)
        remaining = min(size, self.file_size - start)
        chunks: list[bytes] = []
        cursor = start
        while remaining > 0:
            block = self._block(self.block_index_for_offset(cursor))
            within = cursor - block.start_offset
            take = min(remaining, len(block.data) - within)
            if take <= 0:
                break
            chunks.append(block.data[within : within + take])
            cursor += take
            remaining -= take
        return _apply_overlay(start, b"".join(chunks), overlay or {})

    def read_uncached(
        self,
        offset: int,
        size: int,
        overlay: dict[int, bytes] | None = None,
    ) -> bytes:
        data = read_internal_range(self.region, self.mapper, offset, size)
        return _apply_overlay(max(0, offset), data, overlay or {})

    def prefetch_for_offset(self, offset: int, direction: int) -> None:
        block_index = self.block_index_for_offset(offset)
        position = offset % self.block_size
        half = self.block_size // 2
        if direction >= 0 and position >= half:
            self.preload_block(block_index + 1)
        if direction < 0 and position <= half:
            self.preload_block(block_index - 1)

    def preload_block(self, block_index: int) -> None:
        if block_index < 0 or self.cache.has(block_index):
            return
        if block_index * self.block_size >= self.file_size:
            return
        self._block(block_index)

    def _block(self, block_index: int) -> BinaryBlock:
        cached = self.cache.get(block_index)
        if cached is not None:
            return cached
        start = block_index * self.block_size
        data = read_internal_range(self.region, self.mapper, start, self.block_size)
        block = BinaryBlock(block_index, start, start + len(data), data)
        self.cache.put(block)
        return block


def read_internal_range(
    region: InternalFileRegion,
    mapper: InternalOffsetMapper,
    offset: int,
    size: int,
) -> bytes:
    chunks = mapper.chunks_for_internal_range(max(0, offset), size)
    data = bytearray()
    with region.source_path.open("rb") as source:
        for chunk in chunks:
            source.seek(chunk.binary_offset)
            data.extend(source.read(chunk.size))
    return bytes(data)


def export_internal_file_bytes(region: InternalFileRegion) -> bytes:
    mapper = InternalOffsetMapper(region)
    data = bytearray()
    offset = 0
    while True:
        chunk = read_internal_range(region, mapper, offset, INTERNAL_FILE_EXPORT_CHUNK_SIZE)
        if not chunk:
            return bytes(data)
        data.extend(chunk)
        offset += len(chunk)


def _apply_overlay(start: int, data: bytes, overlay: dict[int, bytes]) -> bytes:
    patched = bytearray(data)
    end = start + len(data)
    for patch_offset, patch_data in overlay.items():
        left = max(start, patch_offset)
        right = min(end, patch_offset + len(patch_data))
        if left < right:
            source_left = left - patch_offset
            patched[left - start : right - start] = patch_data[source_left : source_left + right - left]
    return bytes(patched)
