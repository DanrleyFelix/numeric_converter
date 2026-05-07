from pathlib import Path

from src.core.binary_workbench.block_reader import CachedBinaryReader


def test_cached_binary_reader_reads_across_blocks(tmp_path: Path):
    source = tmp_path / "source.bin"
    source.write_bytes(bytes(range(16)))
    reader = CachedBinaryReader(source, block_size=4, cache_max_blocks=8)

    assert reader.block_index_for_offset(9) == 2
    assert reader.read(2, 8) == bytes(range(2, 10))


def test_cached_binary_reader_uses_lru_eviction(tmp_path: Path):
    source = tmp_path / "source.bin"
    source.write_bytes(bytes(range(32)))
    reader = CachedBinaryReader(source, block_size=4, cache_max_blocks=2)

    assert reader.read(0, 4) == bytes(range(4))
    assert reader.read(4, 4) == bytes(range(4, 8))
    assert reader.read(0, 4) == bytes(range(4))
    assert reader.read(8, 4) == bytes(range(8, 12))

    assert len(reader.cache) == 2
    assert reader.cache.has(0)
    assert reader.cache.has(2)
    assert not reader.cache.has(1)


def test_cached_binary_reader_applies_overlay_without_touching_source(tmp_path: Path):
    source = tmp_path / "source.bin"
    source.write_bytes(bytes(range(16)))
    reader = CachedBinaryReader(source, block_size=4, cache_max_blocks=8)

    patched = reader.read(2, 6, {4: bytes.fromhex("AA BB CC DD")})

    assert patched == bytes([2, 3, 0xAA, 0xBB, 0xCC, 0xDD])
    assert source.read_bytes()[4:8] == bytes([4, 5, 6, 7])
