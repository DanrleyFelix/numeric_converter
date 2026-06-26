from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush


@dataclass(frozen=True)
class MaskedBytePattern:
    needle: bytes
    mask: bytes
    alignment: int = 1


def find_masked_bytes_in_data(
    data: bytes,
    base_offset: int,
    pattern: MaskedBytePattern,
    start_offset: int | None = None,
    end_offset: int | None = None,
    max_results: int | None = None,
) -> list[int]:
    if not pattern.needle or len(pattern.needle) != len(pattern.mask):
        return []
    left = max(0, (start_offset or 0) - base_offset)
    right = len(data) if end_offset is None else min(len(data), end_offset - base_offset + 1)
    if right < left or (end_offset is not None and start_offset is not None and start_offset > end_offset):
        return []
    haystack = data[left:right]
    anchor = _anchor_index(pattern.mask)
    if anchor is None:
        return []
    return _anchored_masked_matches(haystack, base_offset + left, pattern, anchor, max_results)


def _anchored_masked_matches(
    haystack: bytes,
    base_offset: int,
    pattern: MaskedBytePattern,
    anchor: int,
    max_results: int | None,
) -> list[int]:
    anchor_mask = pattern.mask[anchor]
    anchor_value = pattern.needle[anchor] & anchor_mask
    candidates = [
        value
        for value in range(256)
        if value & anchor_mask == anchor_value
    ]
    heap: list[tuple[int, int]] = []
    for value in candidates:
        found = haystack.find(bytes((value,)), anchor)
        if found >= 0:
            heappush(heap, (found, value))
    results: list[int] = []
    seen: set[int] = set()
    while heap:
        found, value = heappop(heap)
        start = found - anchor
        absolute = base_offset + start
        if start >= 0 and _aligned(absolute, pattern.alignment) and _matches(haystack, start, pattern):
            if absolute not in seen:
                results.append(absolute)
                seen.add(absolute)
                if max_results is not None and len(results) >= max_results:
                    break
        next_found = haystack.find(bytes((value,)), found + 1)
        if next_found >= 0:
            heappush(heap, (next_found, value))
    return results


def _anchor_index(mask: bytes) -> int | None:
    masked = [(index, _bit_count(value)) for index, value in enumerate(mask) if value]
    if not masked:
        return None
    return max(masked, key=lambda item: item[1])[0]


def _matches(haystack: bytes, start: int, pattern: MaskedBytePattern) -> bool:
    end = start + len(pattern.needle)
    if end > len(haystack):
        return False
    return all(
        haystack[start + index] & mask == pattern.needle[index] & mask
        for index, mask in enumerate(pattern.mask)
    )


def _aligned(offset: int, alignment: int) -> bool:
    return alignment <= 1 or offset % alignment == 0


def _bit_count(value: int) -> int:
    return bin(value).count("1")
