from __future__ import annotations

from collections.abc import Callable
from time import monotonic

from src.core.binary_workbench.search_cache.models import (
    SearchCacheEntry,
    SearchCacheQuery,
)
from src.core.binary_workbench.search_cache.ranges import (
    missing_ranges as uncovered_ranges,
    normalize_ranges,
    offsets_in_range,
)

SEARCH_CACHE_TTL_SECONDS = 60 * 60
SEARCH_CACHE_MAX_ENTRIES = 100


class SearchCacheService:
    def __init__(self, entries: list[SearchCacheEntry] | None = None) -> None:
        self._clock_started = monotonic()
        self._order = 0
        self._entries: dict[str, SearchCacheEntry] = {}
        for entry in entries or []:
            if entry.remaining_seconds <= 0:
                continue
            self._entries[entry.query.key()] = SearchCacheEntry(
                query=entry.query,
                offsets=_unique_offsets(entry.offsets),
                remaining_seconds=min(SEARCH_CACHE_TTL_SECONDS, entry.remaining_seconds),
                ranges=_entry_ranges(entry),
                hit_count=max(1, entry.hit_count),
                last_used_order=entry.last_used_order,
                created_order=entry.created_order,
            )
            self._order = max(self._order, entry.last_used_order, entry.created_order)
        self._evict_overflow()

    def get(
        self,
        query: SearchCacheQuery,
        validator: Callable[[int], bool] | None = None,
    ) -> list[int] | None:
        entry = self._touch(query, validator)
        if entry is None:
            return None
        if self.missing_ranges(query):
            return None
        return offsets_in_range(entry.offsets, _query_range(query))

    def cached_offsets(
        self,
        query: SearchCacheQuery,
        validator: Callable[[int], bool] | None = None,
    ) -> list[int]:
        entry = self._touch(query, validator)
        if entry is None:
            return []
        return offsets_in_range(entry.offsets, _query_range(query))

    def missing_ranges(self, query: SearchCacheQuery) -> list[tuple[int | None, int | None]]:
        self._purge_expired()
        entry = self._entries.get(query.key())
        if entry is None:
            return [_query_range(query)]
        return uncovered_ranges(entry.ranges, _query_range(query))

    def put(
        self,
        query: SearchCacheQuery,
        offsets: list[int],
        hit_count: int = 1,
        remaining_seconds: float = SEARCH_CACHE_TTL_SECONDS,
    ) -> None:
        self._purge_expired()
        key = query.key()
        existing = self._entries.get(key)
        merged_offsets = _unique_offsets([*(existing.offsets if existing else []), *offsets])
        ranges = [*(existing.ranges if existing else []), _query_range(query)]
        order = existing.created_order if existing else self._next_order()
        self._entries[key] = SearchCacheEntry(
            query=query,
            offsets=merged_offsets,
            remaining_seconds=min(SEARCH_CACHE_TTL_SECONDS, max(0.0, remaining_seconds)),
            ranges=normalize_ranges(ranges),
            hit_count=(existing.hit_count + 1) if existing else max(1, hit_count),
            last_used_order=self._next_order(),
            created_order=order,
        )
        self._evict_overflow()

    def entries_for_save(self) -> list[SearchCacheEntry]:
        self._purge_expired()
        return [
            SearchCacheEntry(
                query=entry.query,
                offsets=list(entry.offsets),
                remaining_seconds=self._remaining(entry),
                ranges=list(entry.ranges),
                hit_count=entry.hit_count,
                last_used_order=entry.last_used_order,
                created_order=entry.created_order,
            )
            for entry in self._entries.values()
        ]

    def _remaining(self, entry: SearchCacheEntry) -> float:
        elapsed = monotonic() - self._clock_started
        return max(0.0, entry.remaining_seconds - elapsed)

    def _purge_expired(self) -> None:
        remaining_by_key = {
            key: self._remaining(entry)
            for key, entry in self._entries.items()
        }
        expired = [
            key
            for key, remaining in remaining_by_key.items()
            if remaining <= 0
        ]
        for key in expired:
            self._entries.pop(key, None)
        self._clock_started = monotonic()
        for key, entry in self._entries.items():
            entry.remaining_seconds = remaining_by_key.get(key, entry.remaining_seconds)

    def _evict_overflow(self) -> None:
        while len(self._entries) > SEARCH_CACHE_MAX_ENTRIES:
            key = min(
                self._entries,
                key=lambda item: (
                    self._entries[item].hit_count,
                    self._entries[item].last_used_order,
                ),
            )
            self._entries.pop(key, None)

    def _next_order(self) -> int:
        self._order += 1
        return self._order

    def _touch(
        self,
        query: SearchCacheQuery,
        validator: Callable[[int], bool] | None,
    ) -> SearchCacheEntry | None:
        self._purge_expired()
        entry = self._entries.get(query.key())
        if entry is None:
            return None
        if validator is not None:
            entry.offsets = [offset for offset in entry.offsets if validator(offset)]
        entry.remaining_seconds = SEARCH_CACHE_TTL_SECONDS
        entry.hit_count += 1
        entry.last_used_order = self._next_order()
        return entry


def _query_range(query: SearchCacheQuery) -> tuple[int | None, int | None]:
    return query.start_offset, query.end_offset


def _entry_ranges(entry: SearchCacheEntry) -> list[tuple[int | None, int | None]]:
    if entry.ranges:
        return normalize_ranges(entry.ranges)
    return [_query_range(entry.query)]


def _unique_offsets(offsets: list[int]) -> list[int]:
    return sorted(set(offsets))
