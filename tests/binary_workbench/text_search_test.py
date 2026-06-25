from pathlib import Path

from src.core.binary_workbench.masked_search import find_masked_bytes_in_data
from src.core.binary_workbench.mips_r3000a.instruction_patterns import (
    mips_instruction_byte_pattern,
)
from src.core.binary_workbench.search_cache import (
    SearchCacheQuery,
    SearchCacheRepository,
    SearchCacheService,
)
from src.core.binary_workbench.text_search import ansi_text_bytes, find_bytes_in_rows
from src.modules.dtos import BinaryWorkbenchRowDTO


def test_ansi_text_bytes_uses_windows_ansi_encoding():
    assert ansi_text_bytes("ação") == b"a\xe7\xe3o"


def test_find_bytes_in_rows_respects_optional_offset_range():
    rows = [
        BinaryWorkbenchRowDTO({"File": "0x00000000"}, "", "00 48 45 4C"),
        BinaryWorkbenchRowDTO({"File": "0x00000004"}, "", "4C 4F 00 48"),
        BinaryWorkbenchRowDTO({"File": "0x00000008"}, "", "45 4C 4C 4F"),
    ]

    assert find_bytes_in_rows(rows, b"HELLO") == [1, 7]
    assert find_bytes_in_rows(rows, b"HELLO", start_offset=1, end_offset=5) == [1]
    assert find_bytes_in_rows(rows, b"HELLO", start_offset=7) == [7]
    assert find_bytes_in_rows(rows, b"HELLO", end_offset=5) == [1]


def test_masked_search_finds_partial_mips_instruction_on_word_boundary():
    pattern = mips_instruction_byte_pattern("ADDIU")

    assert pattern is not None
    assert find_masked_bytes_in_data(
        bytes.fromhex("24 00 00 00 F0 FF BD 27 F0 FF BD 27"),
        0,
        pattern,
    ) == [4, 8]


def test_search_cache_refreshes_ttl_and_removes_invalid_offsets():
    query = SearchCacheQuery("bin", "Bytes", "AA", 0, 10, 200)
    cache = SearchCacheService()
    cache.put(query, [0, 4])

    assert cache.get(query, lambda offset: offset != 0) == [4]
    saved = cache.entries_for_save()[0]
    assert saved.offsets == [4]
    assert saved.hit_count == 2


def test_search_cache_extends_range_for_same_pattern():
    first = SearchCacheQuery("bin", "Bytes", "AA", 10, 20, None)
    second = SearchCacheQuery("bin", "Bytes", "AA", 0, 30, None)
    cache = SearchCacheService()
    cache.put(first, [12, 16])

    assert cache.cached_offsets(second) == [12, 16]
    assert cache.missing_ranges(second) == [(0, 9), (21, 30)]

    cache.put(second, [4, 24])
    saved = cache.entries_for_save()[0]

    assert saved.ranges == [(0, 30)]
    assert saved.offsets == [4, 12, 16, 24]


def test_search_cache_keeps_separate_non_contiguous_ranges():
    first = SearchCacheQuery("bin", "Bytes", "AA", 0, 9, None)
    second = SearchCacheQuery("bin", "Bytes", "AA", 20, 29, None)
    requested = SearchCacheQuery("bin", "Bytes", "AA", 0, 29, None)
    cache = SearchCacheService()

    cache.put(first, [4])
    cache.put(second, [24])

    assert cache.cached_offsets(requested) == [4, 24]
    assert cache.missing_ranges(requested) == [(10, 19)]
    assert cache.entries_for_save()[0].ranges == [(0, 9), (20, 29)]


def test_search_cache_repository_persists_remaining_ttl(tmp_path: Path):
    query = SearchCacheQuery("bin", "Bytes", "AA", 0, 10, 200)
    repository = SearchCacheRepository(tmp_path / "cache.json")
    cache = SearchCacheService()
    cache.put(query, [0, 4])

    repository.save(cache.entries_for_save())
    loaded = repository.load()

    assert loaded[0].query == query
    assert loaded[0].offsets == [0, 4]
    assert loaded[0].ranges == [(0, 10)]
    assert loaded[0].remaining_seconds > 0


def test_search_cache_keeps_at_most_one_hundred_searches_without_duplicate_offsets():
    cache = SearchCacheService()
    for index in range(101):
        query = SearchCacheQuery("bin", "Bytes", f"{index:02X}", 0, 10, None)
        cache.put(query, [1, 1, index])

    entries = cache.entries_for_save()

    assert len(entries) == 100
    assert all(entry.offsets == sorted(set(entry.offsets)) for entry in entries)
