from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.modules.utils import read_json, write_json

HAZARD_CACHE_SCHEMA = 1
HAZARD_CACHE_MAX_ENTRIES = 100


@dataclass(frozen=True)
class HazardCacheItem:
    offset: int
    instruction: str
    severity: str = "warning"
    message: str = ""


@dataclass(frozen=True)
class HazardCacheEntry:
    source_id: str
    items: list[HazardCacheItem]


class HazardCacheRepository:
    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def items(
        self,
        source_id: str,
        start_offset: int | None = None,
        end_offset: int | None = None,
    ) -> list[HazardCacheItem]:
        entry = self._entry_for(source_id)
        if entry is None:
            return []
        return sorted(
            [item for item in entry.items if _offset_in_range(item.offset, start_offset, end_offset)],
            key=lambda item: item.offset,
        )

    def replace_range(
        self,
        source_id: str,
        start_offset: int | None,
        end_offset: int | None,
        items: list[HazardCacheItem],
    ) -> list[HazardCacheItem]:
        entries = self.load()
        existing = self._entry_items(entries, source_id)
        merged = {
            item.offset: item
            for item in existing
            if not _offset_in_range(item.offset, start_offset, end_offset)
        }
        for item in items:
            merged[item.offset] = item
        updated = HazardCacheEntry(
            source_id=source_id,
            items=sorted(merged.values(), key=lambda item: item.offset),
        )
        entries = [entry for entry in entries if entry.source_id != source_id]
        if updated.items:
            entries.append(updated)
        self.save(entries[-HAZARD_CACHE_MAX_ENTRIES:])
        return self.items(source_id, start_offset, end_offset)

    def load(self) -> list[HazardCacheEntry]:
        payload = read_json(self._path)
        if not payload or payload.get("schema_version") != HAZARD_CACHE_SCHEMA:
            return []
        entries = payload.get("entries")
        if not isinstance(entries, list):
            return []
        return [entry for item in entries if (entry := _entry_from_payload(item))]

    def save(self, entries: list[HazardCacheEntry]) -> None:
        write_json(
            self._path,
            {
                "schema_version": HAZARD_CACHE_SCHEMA,
                "entries": [_entry_payload(entry) for entry in entries],
            },
        )

    def _entry_for(self, source_id: str) -> HazardCacheEntry | None:
        return next((entry for entry in self.load() if entry.source_id == source_id), None)

    def _entry_items(self, entries: list[HazardCacheEntry], source_id: str) -> list[HazardCacheItem]:
        return next((entry.items for entry in entries if entry.source_id == source_id), [])


def _entry_from_payload(payload: object) -> HazardCacheEntry | None:
    if not isinstance(payload, dict):
        return None
    source_id = payload.get("source_id")
    items = payload.get("items")
    if not isinstance(source_id, str) or not isinstance(items, list):
        return None
    return HazardCacheEntry(
        source_id=source_id,
        items=[item for raw in items if (item := _item_from_payload(raw))],
    )


def _item_from_payload(payload: object) -> HazardCacheItem | None:
    if not isinstance(payload, dict):
        return None
    try:
        return HazardCacheItem(
            offset=_offset_value(payload.get("offset")),
            instruction=str(payload.get("instruction", "")),
            severity=str(payload.get("severity", "warning")),
            message=str(payload.get("message", "")),
        )
    except (TypeError, ValueError):
        return None


def _entry_payload(entry: HazardCacheEntry) -> dict[str, object]:
    return {
        "source_id": entry.source_id,
        "items": [_item_payload(item) for item in entry.items],
    }


def _item_payload(item: HazardCacheItem) -> dict[str, object]:
    return {
        "offset": f"0x{item.offset:08X}",
        "instruction": item.instruction,
        "severity": item.severity,
        "message": item.message,
    }


def _offset_value(value: object) -> int:
    if isinstance(value, int):
        return value
    return int(str(value), 0)


def _offset_in_range(offset: int, start_offset: int | None, end_offset: int | None) -> bool:
    if start_offset is not None and offset < start_offset:
        return False
    if end_offset is not None and offset > end_offset:
        return False
    return True