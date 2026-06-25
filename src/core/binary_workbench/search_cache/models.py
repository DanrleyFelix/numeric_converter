from __future__ import annotations

from dataclasses import dataclass, field

SearchOffsetRange = tuple[int | None, int | None]


@dataclass(frozen=True)
class SearchCacheQuery:
    source_id: str
    mode: str
    value: str
    start_offset: int | None
    end_offset: int | None
    result_limit: int | None

    def key(self) -> str:
        return self.pattern_key()

    def pattern_key(self) -> str:
        return "|".join(
            (
                self.source_id,
                self.mode,
                self.value,
                "" if self.result_limit is None else str(self.result_limit),
            )
        )

    def with_range(self, start_offset: int | None, end_offset: int | None) -> "SearchCacheQuery":
        return SearchCacheQuery(
            source_id=self.source_id,
            mode=self.mode,
            value=self.value,
            start_offset=start_offset,
            end_offset=end_offset,
            result_limit=self.result_limit,
        )


@dataclass
class SearchCacheEntry:
    query: SearchCacheQuery
    offsets: list[int]
    remaining_seconds: float
    ranges: list[SearchOffsetRange] = field(default_factory=list)
    hit_count: int = 1
    last_used_order: int = 0
    created_order: int = 0
