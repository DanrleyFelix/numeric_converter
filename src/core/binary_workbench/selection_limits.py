BYTES_PER_MEGABYTE = 1024 * 1024
DEFAULT_SELECTION_LIMIT_BYTES = 2 * BYTES_PER_MEGABYTE
SELECTION_LIMIT_OPTIONS_BYTES = tuple(
    value * BYTES_PER_MEGABYTE
    for value in (1, 2, 4, 6, 8, 12, 16, 24, 32, 48, 64, 80, 128)
)


def selection_length(start_offset: int, end_offset: int) -> int:
    first, last = sorted((max(0, start_offset), max(0, end_offset)))
    return last - first + 1


def normalized_selection_limit(value: int) -> int:
    if value <= 0:
        return DEFAULT_SELECTION_LIMIT_BYTES
    return min(
        SELECTION_LIMIT_OPTIONS_BYTES,
        key=lambda option: abs(option - value),
    )


def capped_end_offset(
    start_offset: int,
    end_offset: int,
    limit_bytes: int = DEFAULT_SELECTION_LIMIT_BYTES,
) -> int:
    first, last = sorted((max(0, start_offset), max(0, end_offset)))
    limit = normalized_selection_limit(limit_bytes)
    return min(last, first + limit - 1)
