from __future__ import annotations

from pathlib import Path

from src.core.binary_workbench.search_cache.models import (
    SearchCacheEntry,
    SearchCacheQuery,
)
from src.modules.utils import read_json, write_json

SEARCH_CACHE_SCHEMA = 1


class SearchCacheRepository:
    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> list[SearchCacheEntry]:
        payload = read_json(self._path)
        if not payload or payload.get("schema_version") != SEARCH_CACHE_SCHEMA:
            return []
        entries = payload.get("entries")
        if not isinstance(entries, list):
            return []
        return [entry for item in entries if (entry := _entry_from_payload(item))]

    def save(self, entries: list[SearchCacheEntry]) -> None:
        write_json(
            self._path,
            {
                "schema_version": SEARCH_CACHE_SCHEMA,
                "entries": [_entry_payload(entry) for entry in entries],
            },
        )


def _entry_from_payload(payload: object) -> SearchCacheEntry | None:
    if not isinstance(payload, dict):
        return None
    query = payload.get("query")
    offsets = payload.get("offsets")
    if not isinstance(query, dict) or not isinstance(offsets, list):
        return None
    try:
        return SearchCacheEntry(
            query=SearchCacheQuery(
                source_id=str(query["source_id"]),
                mode=str(query["mode"]),
                value=str(query["value"]),
                start_offset=_optional_int(query.get("start_offset")),
                end_offset=_optional_int(query.get("end_offset")),
                result_limit=_optional_int(query.get("result_limit")),
            ),
            offsets=sorted({int(offset) for offset in offsets}),
            remaining_seconds=float(payload.get("remaining_seconds", 0)),
            ranges=_ranges_from_payload(payload.get("ranges")),
            hit_count=int(payload.get("hit_count", 1)),
            last_used_order=int(payload.get("last_used_order", 0)),
            created_order=int(payload.get("created_order", 0)),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _entry_payload(entry: SearchCacheEntry) -> dict[str, object]:
    return {
        "query": {
            "source_id": entry.query.source_id,
            "mode": entry.query.mode,
            "value": entry.query.value,
            "start_offset": entry.query.start_offset,
            "end_offset": entry.query.end_offset,
            "result_limit": entry.query.result_limit,
        },
        "offsets": sorted(set(entry.offsets)),
        "ranges": [[start, end] for start, end in entry.ranges],
        "remaining_seconds": entry.remaining_seconds,
        "hit_count": entry.hit_count,
        "last_used_order": entry.last_used_order,
        "created_order": entry.created_order,
    }


def _optional_int(value: object) -> int | None:
    return None if value in (None, "") else int(value)


def _ranges_from_payload(value: object) -> list[tuple[int | None, int | None]]:
    if not isinstance(value, list):
        return []
    ranges: list[tuple[int | None, int | None]] = []
    for item in value:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            continue
        ranges.append((_optional_int(item[0]), _optional_int(item[1])))
    return ranges
