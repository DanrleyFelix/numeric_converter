"""PSX virtual-to-physical addressing used by Unicorn."""

# KSEG0 and KSEG1 are CPU aliases of the same physical PSX memory space.
PSX_SEGMENT_START = 0x80000000
PSX_SEGMENT_END = 0xBFFFFFFF
PSX_PHYSICAL_MASK = 0x1FFFFFFF


def unicorn_memory_address(address: int) -> int:
    """Translate cached PSX segments to the physical Unicorn address."""

    value = int(address) & 0xFFFFFFFF
    if PSX_SEGMENT_START <= value <= PSX_SEGMENT_END:
        return value & PSX_PHYSICAL_MASK
    return value


def unicorn_mapping_intervals(
    ranges: tuple[tuple[int, int], ...],
    page_size: int,
) -> tuple[tuple[int, int], ...]:
    """Return merged physical page intervals for all debugger ranges."""

    intervals = []
    for start, end in ranges:
        physical_start = unicorn_memory_address(start)
        physical_end = physical_start + end - start + 1
        mapped_start = physical_start & ~(page_size - 1)
        mapped_end = (physical_end + page_size - 1) & ~(page_size - 1)
        intervals.append((mapped_start, mapped_end))
    merged: list[list[int]] = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return tuple((start, end - start) for start, end in merged)
