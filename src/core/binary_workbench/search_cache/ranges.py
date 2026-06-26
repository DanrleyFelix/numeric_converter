from __future__ import annotations

from src.core.binary_workbench.search_cache.models import SearchOffsetRange


def normalize_ranges(ranges: list[SearchOffsetRange]) -> list[SearchOffsetRange]:
    ordered = sorted(ranges, key=lambda item: _start_value(item[0]))
    merged: list[SearchOffsetRange] = []
    for current in ordered:
        if not merged or not _touches(merged[-1], current):
            merged.append(current)
            continue
        merged[-1] = (_min_start(merged[-1][0], current[0]), _max_end(merged[-1][1], current[1]))
    return merged


def missing_ranges(
    covered: list[SearchOffsetRange],
    requested: SearchOffsetRange,
) -> list[SearchOffsetRange]:
    pending = [requested]
    for item in normalize_ranges(covered):
        pending = [part for current in pending for part in _subtract(current, item)]
        if not pending:
            break
    return pending


def offsets_in_range(offsets: list[int], requested: SearchOffsetRange) -> list[int]:
    start, end = requested
    left = _start_value(start)
    return [offset for offset in offsets if offset >= left and (end is None or offset <= end)]


def _subtract(requested: SearchOffsetRange, covered: SearchOffsetRange) -> list[SearchOffsetRange]:
    start, end = requested
    covered_start, covered_end = covered
    left = _start_value(start)
    right = _end_value(end)
    cover_left = _start_value(covered_start)
    cover_right = _end_value(covered_end)
    if cover_right < left or cover_left > right:
        return [requested]
    parts: list[SearchOffsetRange] = []
    if cover_left > left:
        parts.append((start, cover_left - 1))
    if covered_end is not None and cover_right < right:
        parts.append((cover_right + 1, end))
    return parts


def _touches(left: SearchOffsetRange, right: SearchOffsetRange) -> bool:
    left_end = _end_value(left[1])
    right_start = _start_value(right[0])
    return left_end == float("inf") or right_start <= left_end + 1


def _min_start(left: int | None, right: int | None) -> int | None:
    return min(_start_value(left), _start_value(right))


def _max_end(left: int | None, right: int | None) -> int | None:
    if left is None or right is None:
        return None
    return max(left, right)


def _start_value(value: int | None) -> int:
    return 0 if value is None else value


def _end_value(value: int | None) -> int | float:
    return float("inf") if value is None else value
