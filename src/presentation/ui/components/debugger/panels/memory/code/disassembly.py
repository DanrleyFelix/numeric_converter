from __future__ import annotations

from src.core.debugger.memory.image import DebuggerMemoryImage


def refresh_memory_disassembly(debugger, codec, image: DebuggerMemoryImage, address: int, size: int) -> None:
    """Update visible code metadata for every edited instruction slot."""

    step = debugger.step_rules.instruction_size
    first = address - address % step
    for current in range(first, address + size, step):
        if not image.contains(current, step):
            continue
        data = debugger.read_memory(current, step)
        try:
            raw = codec.disassemble(data, current)
            status = "Ready"
        except Exception:
            raw, status = "Invalid instruction", "Invalid"
        debugger.update_instruction(current, data, raw, status)
