from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BinaryBlock:
    block_index: int
    start_offset: int
    end_offset: int
    data: bytes


class BinaryBlockCache:
    def __init__(self, max_blocks: int) -> None:
        self._max_blocks = max(1, max_blocks)
        self._blocks: OrderedDict[int, BinaryBlock] = OrderedDict()

    def has(self, block_index: int) -> bool:
        return block_index in self._blocks

    def get(self, block_index: int) -> BinaryBlock | None:
        block = self._blocks.get(block_index)
        if block is None:
            return None
        self._blocks.move_to_end(block_index)
        return block

    def put(self, block: BinaryBlock) -> None:
        self._blocks[block.block_index] = block
        self._blocks.move_to_end(block.block_index)
        while len(self._blocks) > self._max_blocks:
            self._blocks.popitem(last=False)

    def __len__(self) -> int:
        return len(self._blocks)


class CachedBinaryReader:
    def __init__(self, path: Path, block_size: int, cache_max_blocks: int) -> None:
        self._path = path
        self.block_size = max(1, block_size)
        self.file_size = path.stat().st_size if path.exists() else 0
        self.cache = BinaryBlockCache(cache_max_blocks)
        self._loading_blocks: set[int] = set()

    def block_index_for_offset(self, offset: int) -> int:
        return max(0, offset) // self.block_size

    def read(self, offset: int, size: int, overlay: dict[int, bytes] | None = None) -> bytes:
        if size <= 0 or offset >= self.file_size:
            return b""
        start = max(0, offset)
        remaining = min(size, self.file_size - start)
        chunks: list[bytes] = []
        cursor = start
        while remaining > 0:
            block = self._block_for_offset(cursor)
            within = cursor - block.start_offset
            take = min(remaining, len(block.data) - within)
            chunks.append(block.data[within : within + take])
            cursor += take
            remaining -= take
        return _apply_overlay(start, b"".join(chunks), overlay or {})

    def read_uncached(self, offset: int, size: int, overlay: dict[int, bytes] | None = None) -> bytes:
        if size <= 0 or offset >= self.file_size:
            return b""
        start = max(0, offset)
        read_size = min(size, self.file_size - start)
        with self._path.open("rb") as source:
            source.seek(start)
            data = source.read(read_size)
        return _apply_overlay(start, data, overlay or {})

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

    def _block_for_offset(self, offset: int) -> BinaryBlock:
        return self._block(self.block_index_for_offset(offset))

    def _block(self, block_index: int) -> BinaryBlock:
        cached = self.cache.get(block_index)
        if cached is not None:
            return cached
        if block_index in self._loading_blocks:
            return BinaryBlock(block_index, 0, 0, b"")
        self._loading_blocks.add(block_index)
        start = block_index * self.block_size
        with self._path.open("rb") as source:
            source.seek(start)
            data = source.read(self.block_size)
        block = BinaryBlock(block_index, start, start + len(data), data)
        self.cache.put(block)
        self._loading_blocks.remove(block_index)
        return block


def _apply_overlay(start: int, data: bytes, overlay: dict[int, bytes]) -> bytes:
    if not overlay:
        return data
    patched = bytearray(data)
    end = start + len(data)
    for patch_offset, patch_data in overlay.items():
        patch_end = patch_offset + len(patch_data)
        if patch_end <= start or patch_offset >= end:
            continue
        left = max(start, patch_offset)
        right = min(end, patch_end)
        source_left = left - patch_offset
        patched[left - start : right - start] = patch_data[source_left : source_left + (right - left)]
    return bytes(patched)
