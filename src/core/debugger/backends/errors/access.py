from __future__ import annotations

from src.core.debugger.psx_r3000a.registers import GPR_NAMES

MEMORY_OPCODES = {
    0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26,
    0x28, 0x29, 0x2A, 0x2B, 0x2E,
}


def psx_memory_access_details(
    instruction: bytes,
    registers: dict[str, int],
    fallback: int,
) -> tuple[int, int]:
    """Resolve a failing R3000A load/store effective address and size."""

    if len(instruction) != 4:
        return fallback, 0
    word = int.from_bytes(instruction, "little")
    opcode = word >> 26
    if opcode not in MEMORY_OPCODES:
        return fallback, 0
    base = registers.get(GPR_NAMES[(word >> 21) & 0x1F], 0)
    immediate = word & 0xFFFF
    if immediate & 0x8000:
        immediate -= 0x10000
    size = 1 if opcode in {0x20, 0x24, 0x28} else 2 if opcode in {0x21, 0x25, 0x29} else 4
    return (base + immediate) & 0xFFFFFFFF, size
