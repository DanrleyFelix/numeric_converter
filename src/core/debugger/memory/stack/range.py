"""Automatic virtual-memory range reserved around the initial stack pointer."""

STACK_PAGE_SIZE = 0x1000
ADDRESS_SPACE_END = 0xFFFFFFFF


def debugger_stack_interval(
    stack_pointer: int,
    memory_start: int,
    memory_end: int,
) -> tuple[int, int] | None:
    """Return one zero-filled page when the initial stack is outside the image."""

    value = int(stack_pointer) & ADDRESS_SPACE_END
    if not value or memory_start <= value <= memory_end:
        return None
    start = value & ~(STACK_PAGE_SIZE - 1)
    return start, min(ADDRESS_SPACE_END, start + STACK_PAGE_SIZE - 1)
