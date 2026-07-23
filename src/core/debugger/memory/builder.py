from __future__ import annotations

from collections.abc import Sequence

from src.core.debugger.contracts.registers import BWDebuggerRegs
from src.core.debugger.imports.source import DebuggerResolvedImport
from src.core.debugger.memory.image import (
    DebuggerMemoryImage,
    DebuggerMemoryOverlap,
    DebuggerMemoryZone,
)
from src.core.debugger.memory.stack.range import debugger_stack_interval
from src.core.debugger.models.session import (
    DebuggerDirectiveDocument,
    DebuggerError,
    DebuggerErrorCode,
)

MAX_VIRTUAL_MEMORY_SIZE = 64 * 1024 * 1024
ADDRESS_SPACE_END = 0xFFFFFFFF


def build_debugger_memory(
    document: DebuggerDirectiveDocument,
    imports: Sequence[DebuggerResolvedImport],
    registers: BWDebuggerRegs,
) -> DebuggerMemoryImage:
    """Build a complete zero-filled virtual image or fail transactionally."""

    memory_range = document.memory_range
    if memory_range is None:
        raise _memory_error("The main file does not define virtual_memory_range.")
    size = memory_range.end - memory_range.start + 1
    if size <= 1 or size > MAX_VIRTUAL_MEMORY_SIZE or memory_range.end > ADDRESS_SPACE_END:
        raise _memory_error("The declared virtual memory range is not supported.")
    loaded, zones, overlaps = _loaded_imports(imports, memory_range.start, memory_range.end)
    image = bytearray(size)
    for item, address, source_offset, loaded_size in loaded:
        offset = address - memory_range.start
        image[offset : offset + loaded_size] = item.data[source_offset : source_offset + loaded_size]
    initial_registers = {item.name: 0 for item in registers.descriptors}
    for item in document.register_values:
        bits = registers.register_size(item.register)
        if item.value >= 1 << bits:
            raise _memory_error(f"Initial value for {item.register} exceeds {bits} bits.")
        canonical = next(
            descriptor.name
            for descriptor in registers.descriptors
            if item.register.lstrip("$").casefold()
            in {descriptor.name.casefold(), *(alias.casefold() for alias in descriptor.aliases)}
        )
        initial_registers[canonical] = item.value
    pc_name = registers.pc_register
    initial_pc = initial_registers.get(pc_name, 0)
    if not _valid_initial_pc(initial_pc, zones):
        raise _memory_error("A valid mapped initial PC must be declared with define.")
    for item in document.ignored_addresses:
        registers.register_size(item.register)
    stack_range = debugger_stack_interval(
        initial_registers.get(registers.stack_register, 0),
        memory_range.start,
        memory_range.end,
    )
    snapshot = bytes(image)
    return DebuggerMemoryImage(
        memory_range.start,
        memory_range.end,
        snapshot,
        snapshot,
        zones,
        overlaps,
        stack_range[0] if stack_range else None,
        stack_range[1] if stack_range else None,
        initial_registers,
        initial_pc,
        frozenset(item.address for item in document.ignored_addresses),
    )


def _loaded_imports(
    imports: Sequence[DebuggerResolvedImport],
    start: int,
    end: int,
) -> tuple[
    list[tuple[DebuggerResolvedImport, int, int, int]],
    tuple[DebuggerMemoryZone, ...],
    tuple[DebuggerMemoryOverlap, ...],
]:
    """Clip imports to the image and record only real import overlaps."""

    occupied: list[tuple[int, int, str]] = []
    loaded: list[tuple[DebuggerResolvedImport, int, int, int]] = []
    zones: list[DebuggerMemoryZone] = []
    overlaps: list[DebuggerMemoryOverlap] = []
    for item in imports:
        if item.size <= 0:
            raise _memory_error(f"Import {item.origin} produced no bytes.")
        loaded_start = max(start, item.address)
        loaded_end = min(end, item.end)
        if loaded_start > loaded_end:
            continue
        for first_start, first_end, first_origin in occupied:
            collision_start = max(first_start, loaded_start)
            collision_end = min(first_end, loaded_end)
            if collision_start <= collision_end:
                overlaps.append(
                    DebuggerMemoryOverlap(
                        first_origin,
                        item.origin,
                        collision_start,
                        collision_end,
                    )
                )
        loaded_size = loaded_end - loaded_start + 1
        loaded.append((item, loaded_start, loaded_start - item.address, loaded_size))
        occupied.append((loaded_start, loaded_end, item.origin))
        zones.append(
            DebuggerMemoryZone(loaded_start, loaded_end, item.origin, "Loaded", loaded_size)
        )
    return loaded, tuple(zones), tuple(overlaps)


def _valid_initial_pc(pc: int, zones: tuple[DebuggerMemoryZone, ...]) -> bool:
    """Return whether the initial PC points at a complete mapped instruction."""

    return any(zone.start <= pc and pc + 3 <= zone.end for zone in zones)


def _memory_error(message: str, **details) -> DebuggerError:
    """Create a controlled virtual-memory construction failure."""

    return DebuggerError(DebuggerErrorCode.INVALID_MEMORY, message, details=details)
